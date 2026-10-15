import io
import os
import sys
import tempfile
import unittest
from unittest import mock

import yt_fetch
from yt_fetch import YTFetchError


URL = "https://youtu.be/abc12345678"


class TestYtDlpCommandCannotStart(unittest.TestCase):
    """$YT_DLP_CMD is used without probing, so a wrong one fails at the first yt-dlp call.

    That is a fetch error (exit 3, "yt-dlp not found"), not an OSError traceback.
    """

    def setUp(self):
        missing = os.path.join(tempfile.gettempdir(), "no-such-yt-dlp.exe")
        env = mock.patch.dict(os.environ, {"YT_DLP_CMD": f'"{missing}"'})
        env.start()
        self.addCleanup(env.stop)
        yt_fetch.yt_dlp_cmd.cache_clear()
        self.addCleanup(yt_fetch.yt_dlp_cmd.cache_clear)

    def test_fetch_metadata(self):
        with self.assertRaisesRegex(YTFetchError, "yt-dlp not found: .*fix YT_DLP_CMD"):
            yt_fetch.fetch_metadata(URL)

    def test_fetch_captions(self):
        with self.assertRaisesRegex(YTFetchError, "yt-dlp not found: .*fix YT_DLP_CMD"):
            yt_fetch.fetch_captions_vtt(URL, langs=("en",))

    def test_whisper_audio(self):
        # Get past the ffmpeg and whisper.cpp checks to the yt-dlp audio download.
        whisper = {"WHISPER_CPP_BIN": sys.executable, "WHISPER_MODEL": yt_fetch.__file__}
        with mock.patch.dict(os.environ, whisper), \
                mock.patch.object(yt_fetch.shutil, "which", return_value="ffmpeg"):
            with self.assertRaisesRegex(YTFetchError, "yt-dlp not found: .*fix YT_DLP_CMD"):
                yt_fetch.transcribe_with_whisper(URL)

    def test_main_exits_3(self):
        with tempfile.TemporaryDirectory() as out, \
                mock.patch("sys.stderr", new_callable=io.StringIO) as err:
            self.assertEqual(yt_fetch.main([URL, "--out-dir", out]), 3)
        self.assertIn("yt-dlp not found", err.getvalue())


if __name__ == "__main__":
    unittest.main()
