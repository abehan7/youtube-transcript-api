import requests

try:  # pragma: no cover
    import http.cookiejar as cookiejar

    CookieLoadError = (FileNotFoundError, cookiejar.LoadError)
except ImportError:  # pragma: no cover
    import cookielib as cookiejar

    CookieLoadError = IOError

from ._transcripts import TranscriptListFetcher

from ._errors import CookiePathInvalid, CookiesInvalid


class YouTubeTranscriptApi(object):
    @classmethod
    def list_transcripts(cls, video_id, proxies=None, cookies=None, verify=None):
        """
        Retrieves the list of transcripts which are available for a given video. It returns a `TranscriptList` object
        which is iterable and provides methods to filter the list of transcripts for specific languages. While iterating
        over the `TranscriptList` the individual transcripts are represented by `Transcript` objects, which provide
        metadata and can either be fetched by calling `transcript.fetch()` or translated by calling
        `transcript.translate('en')`. Example::

            # retrieve the available transcripts
            transcript_list = YouTubeTranscriptApi.get('video_id')

            # iterate over all available transcripts
            for transcript in transcript_list:
                # the Transcript object provides metadata properties
                print(
                    transcript.video_id,
                    transcript.language,
                    transcript.language_code,
                    # whether it has been manually created or generated by YouTube
                    transcript.is_generated,
                    # a list of languages the transcript can be translated to
                    transcript.translation_languages,
                )

                # fetch the actual transcript data
                print(transcript.fetch())

                # translating the transcript will return another transcript object
                print(transcript.translate('en').fetch())

            # you can also directly filter for the language you are looking for, using the transcript list
            transcript = transcript_list.find_transcript(['de', 'en'])

            # or just filter for manually created transcripts
            transcript = transcript_list.find_manually_created_transcript(['de', 'en'])

            # or automatically generated ones
            transcript = transcript_list.find_generated_transcript(['de', 'en'])

        :param video_id: the youtube video id
        :type video_id: str
        :param proxies: a dictionary mapping of http and https proxies to be used for the network requests
        :type proxies: {'http': str, 'https': str} - http://docs.python-requests.org/en/master/user/advanced/#proxies
        :param cookies: a string of the path to a text file containing youtube authorization cookies
        :type cookies: str
        :param verify: the path to a CA certificate file or False to ignore verifying the SSL certificate
        :type verify: bool | str - https://docs.python-requests.org/en/latest/user/advanced/#ssl-cert-verification
        :return: the list of available transcripts
        :rtype TranscriptList:
        """
        with requests.Session() as http_client:
            if cookies:
                http_client.cookies = cls._load_cookies(cookies, video_id)
            http_client.proxies = proxies if proxies else {}
            if verify is not None:
                http_client.verify = verify
        
            return TranscriptListFetcher(http_client).fetch(video_id)

    @classmethod
    def get_transcripts(
        cls,
        video_ids,
        languages=("en",),
        continue_after_error=False,
        proxies=None,
        cookies=None,
        preserve_formatting=False,
        verify=None,
    ):
        """
        Retrieves the transcripts for a list of videos.

        :param video_ids: a list of youtube video ids
        :type video_ids: list[str]
        :param languages: A list of language codes in a descending priority. For example, if this is set to ['de', 'en']
        it will first try to fetch the german transcript (de) and then fetch the english transcript (en) if it fails to
        do so.
        :type languages: list[str]
        :param continue_after_error: if this is set the execution won't be stopped, if an error occurs while retrieving
        one of the video transcripts
        :type continue_after_error: bool
        :param proxies: a dictionary mapping of http and https proxies to be used for the network requests
        :type proxies: {'http': str, 'https': str} - http://docs.python-requests.org/en/master/user/advanced/#proxies
        :param cookies: a string of the path to a text file containing youtube authorization cookies
        :type cookies: str
        :param preserve_formatting: whether to keep select HTML text formatting
        :type preserve_formatting: bool
        :param verify: the path to a CA certificate file or False to ignore verifying the SSL certificate
        :type verify: bool | str - https://docs.python-requests.org/en/latest/user/advanced/#ssl-cert-verification
        :return: a tuple containing a dictionary mapping video ids onto their corresponding transcripts, and a list of
        video ids, which could not be retrieved
        :rtype ({str: [{'text': str, 'start': float, 'end': float}]}, [str]}):
        """
        assert isinstance(video_ids, list), "`video_ids` must be a list of strings"

        data = {}
        unretrievable_videos = []

        for video_id in video_ids:
            try:
                data[video_id] = cls.get_transcript(
                    video_id, languages, proxies, cookies, preserve_formatting, verify
                )
            except Exception as exception:
                if not continue_after_error:
                    raise exception

                unretrievable_videos.append(video_id)

        return data, unretrievable_videos

    @classmethod
    def get_transcript(
        cls,
        video_id,
        languages=("en",),
        proxies=None,
        cookies=None,
        preserve_formatting=False,
        verify=None,
    ):
        """
        Retrieves the transcript for a single video. This is just a shortcut for calling::

            YouTubeTranscriptApi.list_transcripts(video_id, proxies).find_transcript(languages).fetch()

        :param video_id: the youtube video id
        :type video_id: str
        :param languages: A list of language codes in a descending priority. For example, if this is set to ['de', 'en']
        it will first try to fetch the german transcript (de) and then fetch the english transcript (en) if it fails to
        do so.
        :type languages: list[str]
        :param proxies: a dictionary mapping of http and https proxies to be used for the network requests
        :type proxies: {'http': str, 'https': str} - http://docs.python-requests.org/en/master/user/advanced/#proxies
        :param cookies: a string of the path to a text file containing youtube authorization cookies
        :type cookies: str
        :param preserve_formatting: whether to keep select HTML text formatting
        :type preserve_formatting: bool
        :param verify: the path to a CA certificate file or False to ignore verifying the SSL certificate
        :type verify: bool | str - https://docs.python-requests.org/en/latest/user/advanced/#ssl-cert-verification
        :return: a list of dictionaries containing the 'text', 'start' and 'duration' keys
        :rtype [{'text': str, 'start': float, 'end': float}]:
        """
        assert isinstance(video_id, str), "`video_id` must be a string"
        return (
            cls.list_transcripts(video_id, proxies, cookies, verify)
            .find_transcript(languages)
            .fetch(preserve_formatting=preserve_formatting)
        )

    @classmethod
    def _load_cookies(cls, cookies, video_id):
        try:
            cookie_jar = cookiejar.MozillaCookieJar()
            cookie_jar.load(cookies)
            if not cookie_jar:
                raise CookiesInvalid(video_id)
            return cookie_jar
        except CookieLoadError:
            raise CookiePathInvalid(video_id)