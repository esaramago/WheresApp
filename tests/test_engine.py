#!/usr/bin/env python3
# Unit tests for WheresApp engine and i18n modules
import os
import sys
import tempfile
import unittest

# Add usr/share/wheresapp to path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHARE_DIR = os.path.join(REPO_ROOT, "usr", "share", "wheresapp")
if SHARE_DIR not in sys.path:
    sys.path.insert(0, SHARE_DIR)

from engine import parse_desktop_file, find_terminal_emulator, SearchEngine, uninstall_application
from i18n import I18n, get_active_locale


class TestI18n(unittest.TestCase):
    """Test localization and locale detection."""

    def test_locale_detection(self):
        self.assertEqual(get_active_locale("pt"), "pt-PT")
        self.assertEqual(get_active_locale("pt_BR.UTF-8"), "pt-PT")
        self.assertEqual(get_active_locale("en"), "en-GB")
        self.assertEqual(get_active_locale("fr_FR.UTF-8"), "en-GB")

    def test_translation_formatting(self):
        i18n_en = I18n("en")
        text = i18n_en.get("confirm_msg_pkg", pkg="test-pkg", ver="1.0", fmt="Snap")
        self.assertIn("test-pkg", text)
        self.assertIn("v1.0", text)
        self.assertIn("[Snap]", text)

        i18n_pt = I18n("pt")
        text_pt = i18n_pt.get("confirm_msg_pkg", pkg="test-pkg", ver="1.0", fmt="Snap")
        self.assertIn("test-pkg", text_pt)
        self.assertIn("Desinstalar", i18n_pt.get("btn_confirm_yes"))


class TestDesktopParser(unittest.TestCase):
    """Test parsing of desktop entry files."""

    def test_parse_regular_desktop(self):
        content = """[Desktop Entry]
Name=Super App
Icon=super-app-icon
Exec=/usr/bin/super-app %U
NoDisplay=false
"""
        with tempfile.NamedTemporaryFile("w", suffix=".desktop", delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            info = parse_desktop_file(temp_path)
            self.assertEqual(info["name"], "Super App")
            self.assertEqual(info["icon"], "super-app-icon")
            self.assertEqual(info["exec"], "/usr/bin/super-app %U")
            self.assertFalse(info["nodisplay"])
            self.assertFalse(info["x_flatpak"])
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_parse_appimage_detection(self):
        content = """[Desktop Entry]
Name=Obsidian
Exec=/home/user/Applications/obsidian.AppImage
"""
        with tempfile.NamedTemporaryFile("w", suffix=".desktop", delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            info = parse_desktop_file(temp_path)
            self.assertIn(".AppImage", info["exec"])
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


class TestTerminalDetection(unittest.TestCase):
    """Test terminal emulator detection."""

    def test_find_terminal(self):
        term, style = find_terminal_emulator()
        # Ensure a terminal emulator is identified on this system
        self.assertIsNotNone(term)
        self.assertIn(style, ["gnome", "konsole", "generic"])


class TestPWAIcon(unittest.TestCase):
    """Test PWA icon fallback creation."""

    def test_pwa_icon_fallback(self):
        from ui import create_app_icon
        from gi.repository import Gtk
        # PWA with empty icon should return a valid Gtk Widget (Image or Box)
        icon_widget = create_app_icon("", app_format="PWA", pixel_size=48)
        self.assertTrue(isinstance(icon_widget, Gtk.Widget))


class TestSystemProtection(unittest.TestCase):
    """Test system package uninstall rejection."""

    def test_system_package_uninstall_refused(self):
        item = {"name": "Kernel", "package": "linux-image", "is_system": True, "format": "Apt"}
        i18n = I18n("en")
        success, msg = uninstall_application(item, i18n)
        self.assertFalse(success)
        self.assertIn("disabled", msg)


if __name__ == "__main__":
    unittest.main()

