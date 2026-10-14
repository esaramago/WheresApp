# Ubuntu App Uninstaller

A lightweight Bash utility with a **Zenity** GUI to easily search for and uninstall **APT**, **Snap**, and **Flatpak** packages on Ubuntu.

---

## 📋 Prerequisites

Before testing or building the package, ensure the required dependencies are installed:

```bash
sudo apt update
sudo apt install zenity gnome-terminal dpkg
```

> **Note:** To search and remove Snap or Flatpak packages, make sure `snapd` and `flatpak` are installed and configured on your system.

---

## 🧪 Testing (Development Mode)

You can run and test the script directly without building or installing the package:

1. Grant execute permissions to the script:
   ```bash
   chmod +x usr/local/bin/uninstaller
   ```

2. Run the script (automatically uses your system locale):
   ```bash
   ./usr/local/bin/uninstaller
   ```

   You can also specify a language manually using `--lang` (or `-l`):
   ```bash
   # Run in Portuguese (pt-PT)
   ./usr/local/bin/uninstaller --lang pt

   # Run in British English (en-GB)
   ./usr/local/bin/uninstaller --lang en
   ```

---

## 🌐 Multi-Language Support (i18n)

The application supports multiple languages and automatically detects your system locale:
- **Portuguese (`pt-PT`)**: Default for any Portuguese system locale (`pt_*`).
- **English (`en-GB`)**: Default fallback for other locales.

Translation files are modular and stored in:
- `usr/share/ubuntu-app-uninstaller/lang/pt-PT.sh`
- `usr/share/ubuntu-app-uninstaller/lang/en-GB.sh`

---

## 📦 Building / Packaging the Debian Package (`.deb`)

This application is written in Bash and does not require binary compilation, but it needs to be **packaged** into a `.deb` file for distribution and system-wide installation.

### Automated Build (Recommended)

Run the included build script from the project root directory:

```bash
./build.sh
```

This script automatically verifies and sets the required file permissions, extracts the version from `DEBIAN/control`, and outputs `ubuntu-app-uninstaller_<version>.deb` (e.g. `ubuntu-app-uninstaller_1.0.deb`).

<details>
<summary>Manual Build Instructions</summary>

1. Set the appropriate permissions:
   ```bash
   chmod 755 DEBIAN
   chmod 644 DEBIAN/control
   chmod 755 usr/local/bin/uninstaller
   chmod 644 usr/share/applications/uninstaller.desktop
   chmod 644 usr/share/pixmaps/*
   ```

2. Build the `.deb` package:
   ```bash
   dpkg-deb --root-owner-group --build . "ubuntu-app-uninstaller_$(awk -F': ' '/^Version:/ {print $2}' DEBIAN/control).deb"
   ```
</details>

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.