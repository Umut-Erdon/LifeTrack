import unittest
from unittest.mock import patch

from automatic_tracker import classify_process, get_foreground_executable


class AutomaticTrackerTests(unittest.TestCase):
    def test_social_app_category(self):
        self.assertEqual(classify_process("Instagram.exe"), ("Instagram", "Sosyal medya"))

    def test_development_tool_category(self):
        self.assertEqual(classify_process("Code.exe"), ("Visual Studio Code", "İş / eğitim"))

    def test_browser_is_not_guessed_as_social_media(self):
        name, category = classify_process("chrome.exe")
        self.assertIn("tarayıcı", name)
        self.assertEqual(category, "Diğer")

    def test_browser_display_name_is_friendly(self):
        self.assertEqual(classify_process("msedge.exe"), ("Microsoft Edge (tarayıcı)", "Diğer"))

    def test_video_app_category(self):
        self.assertEqual(classify_process("Spotify.exe"), ("Spotify", "Video / içerik"))

    def test_unknown_executable_defaults_to_other(self):
        self.assertEqual(classify_process("random-app.exe"), ("Random-app", "Diğer"))

    @patch("automatic_tracker.os.name", "posix")
    def test_unsupported_platform_returns_none(self):
        self.assertIsNone(get_foreground_executable())


if __name__ == "__main__":
    unittest.main()
