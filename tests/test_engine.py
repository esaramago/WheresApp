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

from unittest.mock import patch

from engine import (
    parse_desktop_file,
    find_terminal_emulator,
    SearchEngine,
    uninstall_application,
    launch_application,
    open_in_store,
    can_open_in_store,
    is_store_available,
    is_safe_user_app_dir,
    is_safe_system_desktop_path,
    is_valid_package_name,
    is_system_package_name,
)
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
        self.assertEqual(i18n_en.get("btn_open_store"), "Store")
        self.assertEqual(i18n_en.get("tooltip_open_store"), "Open in Store")

        i18n_pt = I18n("pt")
        text_pt = i18n_pt.get("confirm_msg_pkg", pkg="test-pkg", ver="1.0", fmt="Snap")
        self.assertIn("test-pkg", text_pt)
        self.assertIn("Desinstalar", i18n_pt.get("btn_confirm_yes"))
        self.assertEqual(i18n_pt.get("btn_open_store"), "Loja")
        self.assertEqual(i18n_pt.get("tooltip_open_store"), "Abrir na loja")


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
        try:
            import gi
            gi.require_version("Gtk", "4.0")
            from gi.repository import Gtk
            from ui import create_app_icon
        except (ImportError, ValueError):
            self.skipTest("GTK4 / PyGObject not available")
        # PWA with empty icon should return a valid Gtk Widget (Image or Box)
        icon_widget = create_app_icon("", app_format="PWA", pixel_size=48)
        self.assertTrue(isinstance(icon_widget, Gtk.Widget))


class TestSystemProtection(unittest.TestCase):
    """Test system package uninstall rejection and detection."""

    def test_system_package_uninstall_refused(self):
        item = {"name": "Kernel", "package": "linux-image", "is_system": True, "format": "Apt"}
        i18n = I18n("en")
        success, msg = uninstall_application(item, i18n)
        self.assertFalse(success)
        self.assertIn("disabled", msg)

    def test_system_package_patterns(self):
        self.assertTrue(is_system_package_name("systemd"))
        self.assertTrue(is_system_package_name("systemd-sysv"))
        self.assertTrue(is_system_package_name("udev"))
        self.assertTrue(is_system_package_name("dpkg"))
        self.assertTrue(is_system_package_name("libc6"))
        self.assertTrue(is_system_package_name("linux-image-6.8.0-generic"))
        self.assertTrue(is_system_package_name("linux-headers-6.8.0-generic"))
        self.assertTrue(is_system_package_name("grub-efi-amd64"))
        self.assertFalse(is_system_package_name("curl"))
        self.assertFalse(is_system_package_name("vlc"))

    def test_critical_package_refused_even_when_flag_false(self):
        i18n = I18n("en")
        for pkg in ["linux-image-6.8.0-45-generic", "systemd", "grub-efi-amd64"]:
            item = {"name": pkg, "package": pkg, "is_system": False, "format": "Apt"}
            success, msg = uninstall_application(item, i18n)
            self.assertFalse(success)
            self.assertIn("disabled", msg)


class TestLaunchApplication(unittest.TestCase):
    """Test safe application execution."""

    @patch("engine.subprocess.Popen")
    def test_launch_local_app_safe_args(self, mock_popen):
        item = {
            "format": "Local",
            "name": "Custom Tool",
            "exec": '"/opt/My App/tool" --flag "arg with space" %U',
            "desktop_file": "",
        }
        success, err = launch_application(item)
        self.assertTrue(success)
        self.assertEqual(err, "")
        mock_popen.assert_called_once_with(
            ["/opt/My App/tool", "--flag", "arg with space"],
            start_new_session=True,
        )

    @patch("engine.subprocess.Popen")
    def test_launch_prevents_shell_injection(self, mock_popen):
        item = {
            "format": "AppImage",
            "name": "Malicious App",
            "exec": "/home/user/app.AppImage; rm -rf /",
            "desktop_file": "",
        }
        success, err = launch_application(item)
        self.assertTrue(success)
        called_args, called_kwargs = mock_popen.call_args
        # Arguments must be split into a list without shell execution
        self.assertEqual(called_args[0], ["/home/user/app.AppImage;", "rm", "-rf", "/"])
        self.assertNotIn("shell", called_kwargs)
        self.assertTrue(called_kwargs.get("start_new_session"))


class TestPackageNameValidation(unittest.TestCase):
    """Test package name regex validation for different package formats."""

    def test_apt_package_validation(self):
        self.assertTrue(is_valid_package_name("curl", "Apt"))
        self.assertTrue(is_valid_package_name("python3-gi", "Apt"))
        self.assertTrue(is_valid_package_name("libc6:amd64", "Apt"))
        self.assertTrue(is_valid_package_name("gimp+extra", "Apt"))
        # Flag injection, path traversal, and shell metacharacters must fail
        self.assertFalse(is_valid_package_name("--purge", "Apt"))
        self.assertFalse(is_valid_package_name("-y", "Apt"))
        self.assertFalse(is_valid_package_name("pkg; touch /tmp/pwn", "Apt"))
        self.assertFalse(is_valid_package_name("pkg&echo", "Apt"))
        self.assertFalse(is_valid_package_name("", "Apt"))

    def test_snap_package_validation(self):
        self.assertTrue(is_valid_package_name("vlc", "Snap"))
        self.assertTrue(is_valid_package_name("core22", "Snap"))
        self.assertFalse(is_valid_package_name("--classic", "Snap"))
        self.assertFalse(is_valid_package_name("-snap", "Snap"))
        self.assertFalse(is_valid_package_name("snap; rm -rf /", "Snap"))

    def test_flatpak_package_validation(self):
        self.assertTrue(is_valid_package_name("org.videolan.VLC", "Flatpak"))
        self.assertTrue(is_valid_package_name("com.spotify.Client", "Flatpak"))
        self.assertFalse(is_valid_package_name("--user", "Flatpak"))
        self.assertFalse(is_valid_package_name("-app", "Flatpak"))
        self.assertFalse(is_valid_package_name("org.app; rm", "Flatpak"))


class TestUninstallApplication(unittest.TestCase):
    """Test safe uninstallation command generation."""

    def test_invalid_package_name_rejected(self):
        i18n = I18n("en")
        for bad_pkg in ["--purge", "evil; rm -rf /", "-v", "pkg&evil"]:
            item = {
                "format": "Apt",
                "name": "Bad App",
                "package": bad_pkg,
                "is_system": False,
            }
            success, err = uninstall_application(item, i18n)
            self.assertFalse(success)
            self.assertIn("Invalid package name", err)

    @patch("engine.subprocess.Popen")
    @patch("engine.find_terminal_emulator", return_value=("/usr/bin/gnome-terminal", "gnome"))
    @patch("engine.shutil.which", return_value=None)
    def test_terminal_fallback_uses_safe_quotes_and_separator(self, _mock_which, _mock_term, mock_popen):
        item = {
            "format": "Apt",
            "name": "Valid App",
            "package": "curl",
            "is_system": False,
        }
        i18n = I18n("en")
        success, _ = uninstall_application(item, i18n)
        self.assertTrue(success)
        mock_popen.assert_called_once()
        cmd_args = mock_popen.call_args[0][0]
        self.assertEqual(cmd_args[:3], ["/usr/bin/gnome-terminal", "--", "bash"])
        bash_script = cmd_args[4]
        # Command must include argument separator and package
        self.assertIn("sudo apt remove -- curl;", bash_script)
        self.assertIn("read -p 'Finished! Press Enter to exit...'", bash_script)

    @patch("engine.subprocess.run")
    @patch("engine.shutil.which")
    def test_pkexec_command_has_argument_separator(self, mock_which, mock_run):
        mock_which.side_effect = lambda cmd: "/usr/bin/pkexec" if cmd == "pkexec" else None
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = ""

        item = {
            "format": "Snap",
            "name": "Snap App",
            "package": "vlc",
            "is_system": False,
        }
        i18n = I18n("en")
        success, _ = uninstall_application(item, i18n)
        self.assertTrue(success)
        mock_run.assert_called_once_with(
            ["pkexec", "snap", "remove", "--", "vlc"],
            capture_output=True,
            text=True,
        )


class TestSafePathValidation(unittest.TestCase):
    """Test safety checks for directory and desktop file paths."""

    def test_user_app_dir_rejects_critical_paths(self):
        home = os.path.expanduser("~")
        # Direct home directory
        self.assertFalse(is_safe_user_app_dir(home))
        # Top-level standard folders
        self.assertFalse(is_safe_user_app_dir(os.path.join(home, "Documents")))
        self.assertFalse(is_safe_user_app_dir(os.path.join(home, "Downloads")))
        self.assertFalse(is_safe_user_app_dir(os.path.join(home, ".local")))
        self.assertFalse(is_safe_user_app_dir(os.path.join(home, ".local", "share")))
        self.assertFalse(is_safe_user_app_dir(os.path.join(home, ".local", "bin")))
        self.assertFalse(is_safe_user_app_dir(os.path.join(home, ".local", "share", "applications")))
        # Nested subdirectories inside protected user folders
        self.assertFalse(is_safe_user_app_dir(os.path.join(home, "Documents", "Work")))
        self.assertFalse(is_safe_user_app_dir(os.path.join(home, "Downloads", "Folder")))
        self.assertFalse(is_safe_user_app_dir(os.path.join(home, ".ssh", "keys")))
        self.assertFalse(is_safe_user_app_dir(os.path.join(home, ".config", "myapp")))
        self.assertFalse(is_safe_user_app_dir(os.path.join(home, ".local", "bin", "subdir")))
        self.assertFalse(is_safe_user_app_dir(os.path.join(home, ".local", "share", "applications", "sub")))
        self.assertFalse(is_safe_user_app_dir(os.path.join(home, ".local", "share", "icons")))
        # System directories outside home
        self.assertFalse(is_safe_user_app_dir("/etc"))
        self.assertFalse(is_safe_user_app_dir("/usr/bin"))

    def test_user_app_dir_allows_nested_app_folders(self):
        home = os.path.expanduser("~")
        # Dedicated application folders
        self.assertTrue(is_safe_user_app_dir(os.path.join(home, "Applications", "Obsidian")))
        self.assertTrue(is_safe_user_app_dir(os.path.join(home, ".local", "share", "myapp")))

    def test_system_desktop_path_validation(self):
        self.assertTrue(is_safe_system_desktop_path("/usr/share/applications/firefox.desktop"))
        self.assertTrue(is_safe_system_desktop_path("/usr/local/share/applications/custom.desktop"))
        self.assertFalse(is_safe_system_desktop_path("/etc/shadow"))
        self.assertFalse(is_safe_system_desktop_path("/home/user/.local/share/applications/test.desktop"))

    @patch("engine.shutil.rmtree")
    @patch("engine.os.remove")
    def test_uninstall_refuses_to_delete_home_folder(self, _mock_remove, mock_rmtree):
        home = os.path.expanduser("~")
        with tempfile.NamedTemporaryFile("w", suffix=".desktop", delete=False) as f:
            f.write(f"[Desktop Entry]\nName=Dangerous\nExec={home}\n")
            temp_path = f.name

        try:
            item = {
                "format": "Local",
                "name": "Dangerous App",
                "package": "dangerous",
                "desktop_file": temp_path,
                "is_system": False,
            }
            i18n = I18n("en")
            success, _ = uninstall_application(item, i18n)
            self.assertTrue(success)
            # rmtree must never be called on home
            mock_rmtree.assert_not_called()
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


class TestDesktopMapping(unittest.TestCase):
    """Test package-to-desktop entry mapping in SearchEngine."""

    def test_arch_qualified_package_lookup(self):
        engine = SearchEngine()
        engine.cached_desktop_map["test-app"] = ("Test Application", "/usr/share/applications/test.desktop", "test-icon")

        with patch("engine.subprocess.run") as mock_run:
            mock_run.return_value.stdout = "installed\ttest-app:amd64\t1.0\toptional\tno\tno\n"
            results = engine.search_apt("test")
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["name"], "Test Application")
            self.assertEqual(results[0]["icon"], "test-icon")
            self.assertEqual(results[0]["desktop_file"], "/usr/share/applications/test.desktop")

    def test_dpkg_s_populates_desktop_map(self):
        engine = SearchEngine()
        # Ensure cached_desktop_map contains mapped entries
        if "gnome-calculator" in engine.cached_desktop_map:
            name, path, icon = engine.cached_desktop_map["gnome-calculator"]
            self.assertEqual(name, "Calculator")
            self.assertTrue(path.endswith(".desktop"))
            self.assertEqual(icon, "org.gnome.Calculator")


class TestAppStreamMetaInfo(unittest.TestCase):
    """Test AppStream metainfo specification and required fields."""

    def test_metainfo_file_fields(self):
        import xml.etree.ElementTree as ET
        metainfo_path = os.path.join(REPO_ROOT, "usr", "share", "metainfo", "com.github.esaramago.wheresapp.metainfo.xml")
        self.assertTrue(os.path.isfile(metainfo_path))

        tree = ET.parse(metainfo_path)
        root = tree.getroot()
        self.assertEqual(root.tag, "component")
        self.assertEqual(root.attrib.get("type"), "desktop-application")

        license_elem = root.find("project_license")
        self.assertIsNotNone(license_elem)
        self.assertEqual(license_elem.text, "MIT")

        homepage = root.find("./url[@type='homepage']")
        self.assertIsNotNone(homepage)
        self.assertTrue(homepage.text.startswith("https://github.com/"))

        releases = root.findall("./releases/release")
        self.assertGreater(len(releases), 0)
        latest_release = releases[0]
        self.assertIn("version", latest_release.attrib)
        self.assertIn("date", latest_release.attrib)

    def test_appstreamcli_validation(self):
        import shutil, subprocess
        appstreamcli = shutil.which("appstreamcli")
        if not appstreamcli:
            self.skipTest("appstreamcli not found")

        metainfo_path = os.path.join(REPO_ROOT, "usr", "share", "metainfo", "com.github.esaramago.wheresapp.metainfo.xml")
        res = subprocess.run([appstreamcli, "validate", "--no-net", metainfo_path], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"appstreamcli validation failed:\n{res.stdout}\n{res.stderr}")


class TestOpenInStore(unittest.TestCase):
    """Test opening applications in their respective software store."""

    @patch("engine.is_store_available", return_value=True)
    def test_can_open_in_store_supported_formats(self, _mock_store):
        self.assertTrue(can_open_in_store({"format": "Apt", "package": "gedit"}))
        self.assertTrue(can_open_in_store({"format": "Snap", "package": "firefox"}))
        self.assertTrue(can_open_in_store({"format": "Flatpak", "package": "org.gnome.Calculator"}))

    @patch("engine.is_store_available", return_value=True)
    def test_can_open_in_store_unsupported_formats(self, _mock_store):
        self.assertFalse(can_open_in_store({"format": "Local", "package": "custom-app"}))
        self.assertFalse(can_open_in_store({"format": "AppImage", "package": "obsidian"}))
        self.assertFalse(can_open_in_store({"format": "PWA", "package": "notion"}))

    @patch("engine.is_store_available", return_value=False)
    def test_can_open_in_store_no_store(self, _mock_store):
        self.assertFalse(can_open_in_store({"format": "Apt", "package": "gedit"}))
        self.assertFalse(can_open_in_store({"format": "Snap", "package": "firefox"}))
        self.assertFalse(can_open_in_store({"format": "Flatpak", "package": "org.gnome.Calculator"}))

    @patch("engine.can_open_in_store", return_value=False)
    def test_open_in_store_unsupported_fails(self, _mock_can_open):
        item = {"format": "AppImage", "package": "test"}
        success, err = open_in_store(item)
        self.assertFalse(success)
        self.assertIn("cannot be opened in a store", err)

    @patch("engine.can_open_in_store", return_value=True)
    @patch("engine.shutil.which")
    @patch("engine.subprocess.Popen")
    def test_open_in_store_snap(self, mock_popen, mock_which, _mock_can_open):
        mock_which.side_effect = lambda cmd: "/snap/bin/snap-store" if cmd == "snap-store" else None
        item = {"format": "Snap", "package": "firefox", "name": "Firefox"}
        success, _ = open_in_store(item)
        self.assertTrue(success)
        mock_popen.assert_called_once_with(["snap-store", "snap://firefox"], start_new_session=True)

    @patch("engine.can_open_in_store", return_value=True)
    @patch("engine.shutil.which")
    @patch("engine.subprocess.Popen")
    def test_open_in_store_flatpak(self, mock_popen, mock_which, _mock_can_open):
        mock_which.side_effect = lambda cmd: "/usr/bin/gnome-software" if cmd == "gnome-software" else None
        item = {"format": "Flatpak", "package": "org.gnome.Calculator", "name": "Calculator"}
        success, _ = open_in_store(item)
        self.assertTrue(success)
        mock_popen.assert_called_once_with(["gnome-software", "--details=org.gnome.Calculator"], start_new_session=True)

    @patch("engine.can_open_in_store", return_value=True)
    @patch("engine.shutil.which")
    @patch("engine.subprocess.Popen")
    def test_open_in_store_apt(self, mock_popen, mock_which, _mock_can_open):
        mock_which.side_effect = lambda cmd: "/usr/bin/gnome-software" if cmd == "gnome-software" else None
        item = {"format": "Apt", "package": "gedit", "name": "Text Editor", "desktop_file": "/usr/share/applications/org.gnome.gedit.desktop"}
        success, _ = open_in_store(item)
        self.assertTrue(success)
        mock_popen.assert_called_once_with(["gnome-software", "--details-pkg=gedit"], start_new_session=True)


if __name__ == "__main__":
    unittest.main()



