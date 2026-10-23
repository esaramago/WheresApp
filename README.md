# WheresApp

A modern **GTK 4** and **Libadwaita** desktop utility to find, launch, and uninstall **APT**, **Snap**, **Flatpak**, **AppImage**, **PWA**, and **Local** applications on Ubuntu.

---

## 📋 Prerequisites

Before testing or building the package, ensure the required dependencies are installed:

```bash
sudo apt update
sudo apt install python3 python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 dpkg
```

> **Note:** To search and manage Snap or Flatpak packages, make sure `snapd` and `flatpak` are installed and configured on your system.

---

## 🧪 Testing (Development Mode)

You can run and test the script directly without building or installing the package:

1. Grant execute permissions to the script:
   ```bash
   chmod +x usr/local/bin/wheresapp usr/local/bin/uninstaller
   ```

2. Run the script (automatically uses your system locale):
   ```bash
   ./usr/local/bin/wheresapp
   ```

   You can also specify a language manually using `--lang` (or `-l`):
   ```bash
   # Run in Portuguese (pt-PT)
   ./usr/local/bin/wheresapp --lang pt

   # Run in British English (en-GB)
   ./usr/local/bin/wheresapp --lang en
   ```

---

## 🌐 Multi-Language Support (i18n)

The application supports multiple languages and automatically detects your system locale:
- **Portuguese (`pt-PT`)**: Default for Portuguese system locales (`pt_*`).
- **English (`en-GB`)**: Default fallback for other locales.

Translation modules are stored in:
- `usr/share/wheresapp/i18n.py`
- Shell fallback definitions: `usr/share/wheresapp/lang/`

---

## 📦 Building / Packaging the Debian Package (`.deb`)

This application is written in Python 3 (PyGObject) and does not require binary compilation, but it can be packaged into a `.deb` file for distribution and system-wide installation.

### Automated Build (Recommended)

Run the included build script from the project root directory:

```bash
./build.sh
```

This script sets the required file permissions, extracts the version from `DEBIAN/control`, and creates `wheresapp_<version>.deb` (e.g. `wheresapp_2.0.deb`).

<details>
<summary>Manual Build Instructions</summary>

1. Set the appropriate permissions:
   ```bash
   chmod 755 DEBIAN
   chmod 644 DEBIAN/control
   chmod 755 usr/local/bin/*
   chmod 644 usr/share/applications/*
   chmod 644 usr/share/pixmaps/*
   ```

2. Build the `.deb` package:
   ```bash
   dpkg-deb --root-owner-group --build . "wheresapp_$(awk -F': ' '/^Version:/ {print $2}' DEBIAN/control | tr -d '[:space:]').deb"
   ```
</details>

---

## 🤝 Contributing

Contributions are welcome! Please check out the [Contributing Guidelines](CONTRIBUTING.md) for details on setting up your development environment, coding standards, testing, and submitting pull requests.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.