# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.0]

### Added
- Added "Open in Store" feature (`open_in_store`, `can_open_in_store`, and `is_store_available`) allowing users to inspect APT, Snap, and Flatpak packages in compatible software centers (GNOME Software, Snap Store, Ubuntu App Center, KDE Discover, Linux Mint Software Manager, Elementary AppCenter).
- Added "Store" action button on application cards with dedicated tooltips and automatic sensitivity states.
- Added internationalization keys (`btn_open_store`, `tooltip_open_store`, `store_unavailable`, `opening_store`, `open_store_failed`) in English and Portuguese.
- Added unit tests for software store detection and URL/command handling.

### Changed
- Updated application branding icons (`wheresapp.svg` and `wheresapp.png`).

---

## [1.2.1] - 2026-10-14

### Added
- Debian package to desktop entry reverse mapping using `dpkg -S`.
- `Homepage` field in `DEBIAN/control` metadata.
- AppStream metainfo validation tests using `appstreamcli`.

### Security
- Fixed path traversal vulnerabilities with safe directory checking (`is_safe_user_app_dir`, `is_safe_system_desktop_path`).
- Added package name validation (`is_valid_package_name`) to prevent command and argument injection during package removal.

---

## [1.2.0] - 2026-10-14

### Added
- Complete UI rewrite and migration to GTK 4 and Libadwaita (`Adw.ApplicationWindow`, `Adw.Clamp`, `Adw.Toast`).
- Responsive two-column card grid layout for browsing applications.
- Integrated in-app uninstallation workflow powered by PolicyKit (`pkexec`) with progress feedback and automatic return to search.
- Protection against removing critical system packages, featuring status badges and disabled uninstall actions.
- Dedicated fallback icon for Progressive Web Apps (PWAs).
- AppStream metainfo file (`com.github.esaramago.wheresapp.metainfo.xml`).

### Changed
- Rebranded application from `ubuntu-app-uninstaller` to **WheresApp**.
- Redesigned card action buttons with typography sizing, equal dimensions, and ellipsis truncation for long labels.

### Removed
- Legacy Zenity dialog interface and standalone uninstaller desktop entry.

---

## [1.1.0] - 2026-10-14

### Added
- Expanded scope from package uninstaller to application finder and launcher.
- Detection and launching support for AppImage and Progressive Web Apps (PWAs).

---

## [1.0.0] - 2026-09-22

### Added
- Initial release as `ubuntu-app-uninstaller`.
- Search and uninstallation support for APT, Snap, and Flatpak applications.
- Zenity-based graphical dialogs with search re-prompting and back navigation.
- Internationalization (i18n) with English (`en-GB`) and Portuguese (`pt-PT`) language support.
- System package status indicator and cautionary warnings.

[Unreleased]: https://github.com/esaramago/ubuntu-app-uninstaller/compare/v3.1...HEAD
[3.1]: https://github.com/esaramago/ubuntu-app-uninstaller/compare/v3.0...v3.1
[3.0]: https://github.com/esaramago/ubuntu-app-uninstaller/compare/v2.0...v3.0
[2.0]: https://github.com/esaramago/ubuntu-app-uninstaller/compare/v1.0.0...v2.0
[1.0.0]: https://github.com/esaramago/ubuntu-app-uninstaller/releases/tag/v1.0.0
