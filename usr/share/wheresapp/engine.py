#!/usr/bin/env python3
# Backend search, launch, and uninstall engine for WheresApp
import glob
import os
import re
import shlex
import shutil
import subprocess


def parse_desktop_file(path: str) -> dict:
    """Parse key desktop file fields."""
    info = {
        "name": "",
        "icon": "",
        "exec": "",
        "nodisplay": False,
        "x_flatpak": False,
        "x_snap": False,
    }
    if not os.path.isfile(path):
        return info

    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if line.startswith("Name=") and not info["name"]:
                    info["name"] = line[5:].strip()
                elif line.startswith("Icon=") and not info["icon"]:
                    info["icon"] = line[5:].strip()
                elif line.startswith("Exec=") and not info["exec"]:
                    info["exec"] = line[5:].strip()
                elif line.lower() == "nodisplay=true":
                    info["nodisplay"] = True
                elif line.startswith("X-Flatpak=") or line.startswith("X-SnapInstanceName="):
                    info["x_flatpak"] = True
    except Exception:
        pass
    return info


def find_terminal_emulator() -> tuple[str | None, str]:
    """Find an available terminal emulator and its argument format."""
    candidates = [
        ("gnome-terminal", "gnome"),
        ("ptyxis", "gnome"),
        ("kgx", "gnome"),
        ("xfce4-terminal", "gnome"),
        ("konsole", "konsole"),
        ("x-terminal-emulator", "generic"),
        ("xterm", "generic"),
    ]
    for binary, style in candidates:
        path = shutil.which(binary)
        if path:
            return path, style
    return None, ""


def is_safe_user_app_dir(path: str) -> bool:
    """Validate that path is a dedicated application folder before deletion."""
    try:
        real_path = os.path.realpath(os.path.abspath(os.path.expanduser(path)))
        home_dir = os.path.realpath(os.path.expanduser("~"))

        # Must reside strictly inside the user's home directory
        if not real_path.startswith(home_dir + os.sep):
            return False

        rel = os.path.relpath(real_path, home_dir)
        parts = rel.split(os.sep)

        # Must be at least 2 levels deep inside home (e.g., .local/share/myapp)
        if len(parts) < 2:
            return False

        # Protect standard top-level user directories and all their subdirectories
        forbidden_top_dirs = {
            ".config",
            ".cache",
            ".ssh",
            ".gnupg",
            ".mozilla",
            ".pki",
            ".thunderbird",
            "Desktop",
            "Documents",
            "Downloads",
            "Music",
            "Pictures",
            "Public",
            "Templates",
            "Videos",
            "bin",
        }
        if parts[0] in forbidden_top_dirs:
            return False

        # Inside .local, only allow dedicated app folders under .local/share/<app>
        if parts[0] == ".local":
            if len(parts) < 3 or parts[1] != "share":
                return False
            forbidden_local_share_dirs = {
                "applications",
                "backgrounds",
                "color-schemes",
                "dbus-1",
                "flatpak",
                "fonts",
                "gnome-shell",
                "gvfs-metadata",
                "icons",
                "keyrings",
                "mime",
                "nautilus",
                "sounds",
                "systemd",
                "themes",
                "Trash",
                "wallpapers",
            }
            if parts[2] in forbidden_local_share_dirs:
                return False

        return True
    except Exception:
        return False


def is_safe_system_desktop_path(path: str) -> bool:
    """Validate that desktop file path is inside allowed system application directories."""
    try:
        abs_path = os.path.abspath(path)
        if os.path.islink(abs_path):
            return False
        real = os.path.realpath(abs_path)
        allowed_dirs = ["/usr/share/applications", "/usr/local/share/applications"]
        return (
            os.path.dirname(abs_path) in allowed_dirs
            and any(real.startswith(d + os.sep) for d in allowed_dirs)
            and real.endswith(".desktop")
        )
    except Exception:
        return False


def is_valid_package_name(pkg: str, fmt: str) -> bool:
    """Validate package identifier format based on package manager."""
    if not pkg or len(pkg) > 255:
        return False

    if fmt == "Apt":
        # Debian package names: alphanumeric, plus, minus, period, colon (for multiarch)
        return bool(re.match(r"^[a-zA-Z0-9][a-zA-Z0-9+.:~-]*$", pkg))

    if fmt == "Snap":
        # Snap names: alphanumeric and hyphens, cannot start with hyphen
        return bool(re.match(r"^[a-zA-Z0-9][a-zA-Z0-9-]*$", pkg))

    if fmt == "Flatpak":
        # Flatpak reverse DNS identifiers: alphanumeric, dots, hyphens, underscores
        return bool(re.match(r"^[a-zA-Z0-9_.-]+$", pkg) and not pkg.startswith("-"))

    if fmt in ["Local", "AppImage", "PWA"]:
        return bool(re.match(r"^[a-zA-Z0-9_.-]+$", pkg) and not pkg.startswith("-"))

    return False


def is_system_package_name(pkg: str) -> bool:
    """Check if package name matches critical system packages or patterns."""
    pkg_lower = pkg.lower()

    # Core essential packages that must never be uninstalled
    core_pkgs = {
        "systemd",
        "systemd-sysv",
        "udev",
        "init",
        "dpkg",
        "apt",
        "libc6",
        "libc-bin",
        "base-files",
        "base-passwd",
        "linux-base",
        "linux-firmware",
        "grub-pc",
        "grub-common",
        "shim-signed",
        "network-manager",
        "netplan.io",
        "wpasupplicant",
        "sudo",
        "polkitd",
        "policykit-1",
    }
    if pkg_lower in core_pkgs:
        return True

    # Core system package prefixes (kernels, modules, bootloaders)
    prefixes = (
        "linux-image-",
        "linux-headers-",
        "linux-modules-",
        "grub-efi-",
        "systemd-",
    )
    return any(pkg_lower.startswith(p) for p in prefixes)


class SearchEngine:
    """Application search and package discovery engine."""

    def __init__(self):
        self.cached_sys_pkgs: set[str] = set()
        self.cached_desktop_map: dict[str, tuple[str, str, str]] = {}
        self.init_cache()

    def init_cache(self):
        """Pre-populate system package dependencies and desktop file maps."""
        # Index system desktop files in /usr/share/applications
        desktop_files = glob.glob("/usr/share/applications/*.desktop")
        for path in desktop_files:
            info = parse_desktop_file(path)
            if info["name"] and not info["nodisplay"]:
                pkg_key = os.path.splitext(os.path.basename(path))[0]
                self.cached_desktop_map[pkg_key] = (info["name"], path, info["icon"])

        # Map Debian package names to desktop entries using dpkg -S
        dpkg_bin = shutil.which("dpkg")
        if dpkg_bin and desktop_files:
            try:
                res = subprocess.run(
                    [dpkg_bin, "-S"] + desktop_files,
                    capture_output=True,
                    text=True,
                )
                for line in res.stdout.splitlines():
                    if ": " not in line:
                        continue
                    pkg_section, file_path = line.split(": ", 1)
                    file_path = file_path.strip()
                    info = parse_desktop_file(file_path)
                    if not info["name"] or info["nodisplay"]:
                        continue
                    for p in pkg_section.split(","):
                        pkg_name = p.split(":")[0].strip()
                        if not pkg_name:
                            continue
                        base = os.path.splitext(os.path.basename(file_path))[0]
                        if pkg_name not in self.cached_desktop_map or base == pkg_name:
                            self.cached_desktop_map[pkg_name] = (info["name"], file_path, info["icon"])
            except Exception:
                pass

        # Cache base Ubuntu, Debian, and Mint system metapackages
        metapackages = [
            "ubuntu-desktop-minimal",
            "ubuntu-desktop",
            "ubuntu-standard",
            "ubuntu-minimal",
            "task-desktop",
            "task-gnome-desktop",
            "task-xfce-desktop",
            "task-kde-desktop",
            "debian-core",
            "mint-meta-core",
            "mint-meta-cinnamon",
        ]
        try:
            res = subprocess.run(
                ["dpkg-query", "-W", "-f=${Package}\\n"] + metapackages,
                capture_output=True,
                text=True,
            )
            for pkg in res.stdout.splitlines():
                if pkg.strip():
                    self.cached_sys_pkgs.add(pkg.strip())

            res2 = subprocess.run(
                ["apt-cache", "depends"] + metapackages,
                capture_output=True,
                text=True,
            )
            for line in res2.stdout.splitlines():
                line = line.strip()
                if line.startswith("Depends:") or line.startswith("Recommends:"):
                    dep = line.split(":", 1)[1].strip().replace("<", "").replace(">", "").split()
                    if dep:
                        self.cached_sys_pkgs.add(dep[0])
        except Exception:
            pass

    def search_flatpak(self, query: str) -> list[dict]:
        """Search Flatpak applications."""
        results = []
        if not shutil.which("flatpak"):
            return results

        try:
            res = subprocess.run(
                ["flatpak", "list", "--columns=name:f,application:f,version:f"],
                capture_output=True,
                text=True,
            )
            q = query.lower()
            for line in res.stdout.splitlines():
                parts = line.split("\t")
                if len(parts) >= 2:
                    name = parts[0].strip() or "-"
                    app_id = parts[1].strip() or "-"
                    ver = parts[2].strip() if len(parts) > 2 else "-"
                    full = f"{name} {app_id}".lower()
                    if q in full:
                        results.append({
                            "name": name,
                            "package": app_id,
                            "version": ver or "-",
                            "format": "Flatpak",
                            "is_system": False,
                            "icon": app_id,
                            "desktop_file": "",
                        })
        except Exception:
            pass
        return results

    def search_snap(self, query: str) -> list[dict]:
        """Search Snap applications."""
        results = []
        if not shutil.which("snap"):
            return results

        try:
            res = subprocess.run(["snap", "list"], capture_output=True, text=True)
            lines = res.stdout.splitlines()
            if len(lines) <= 1:
                return results

            q = query.lower()
            for line in lines[1:]:
                parts = line.split()
                if not parts:
                    continue
                pkg = parts[0]
                ver = parts[1] if len(parts) > 1 else "-"
                notes = " ".join(parts[2:]) if len(parts) > 2 else ""

                # Look up desktop file for human-friendly name and icon
                desktop_candidates = (
                    glob.glob(f"/var/lib/snapd/desktop/applications/{pkg}_*.desktop")
                    + glob.glob(f"/var/lib/snapd/desktop/applications/{pkg}.desktop")
                )
                name = pkg
                icon = pkg
                desktop_file = ""
                if desktop_candidates and os.path.isfile(desktop_candidates[0]):
                    desktop_file = desktop_candidates[0]
                    d_info = parse_desktop_file(desktop_file)
                    if d_info["name"]:
                        name = d_info["name"]
                    if d_info["icon"]:
                        icon = d_info["icon"]

                full = f"{name} {pkg}".lower()
                if q in full:
                    is_sys = False
                    if pkg in ["snapd", "core", "bare", "gtk-common-themes"] or pkg.startswith("core") or pkg.startswith("gnome-"):
                        is_sys = True
                    elif "base" in notes or "snapd" in notes:
                        is_sys = True

                    results.append({
                        "name": name,
                        "package": pkg,
                        "version": ver,
                        "format": "Snap",
                        "is_system": is_sys,
                        "icon": icon,
                        "desktop_file": desktop_file,
                    })
        except Exception:
            pass
        return results

    def search_local(self, query: str) -> list[dict]:
        """Search Local, AppImage, and PWA applications."""
        results = []
        local_dirs = [
            os.path.expanduser("~/.local/share/applications"),
            "/usr/local/share/applications",
        ]
        q = query.lower()

        for l_dir in local_dirs:
            if not os.path.isdir(l_dir):
                continue
            for d_file in glob.glob(os.path.join(l_dir, "*.desktop")):
                if not os.path.isfile(d_file):
                    continue
                info = parse_desktop_file(d_file)
                if info["nodisplay"] or info["x_flatpak"]:
                    continue
                name = info["name"]
                if not name:
                    continue

                pkg = os.path.splitext(os.path.basename(d_file))[0]
                full = f"{name} {pkg}".lower()
                if q in full:
                    exec_cmd = info["exec"]
                    fmt = "Local"
                    if ".AppImage" in exec_cmd or ".appimage" in exec_cmd.lower():
                        fmt = "AppImage"
                    elif "--app=" in exec_cmd or "--app-id=" in exec_cmd or "chrome-extension:" in exec_cmd:
                        fmt = "PWA"

                    results.append({
                        "name": name,
                        "package": pkg,
                        "version": "-",
                        "format": fmt,
                        "is_system": False,
                        "icon": info["icon"] or pkg,
                        "desktop_file": d_file,
                        "exec": exec_cmd,
                    })
        return results

    def search_apt(self, query: str) -> list[dict]:
        """Search APT installed packages."""
        results = []
        if not shutil.which("dpkg-query"):
            return results

        q = query.lower()
        try:
            fmt = "${db:Status-Status}\\t${Package}\\t${Version}\\t${Priority}\\t${Essential}\\t${Protected}\\n"
            res = subprocess.run(
                ["dpkg-query", "-W", "-f=" + fmt],
                capture_output=True,
                text=True,
            )
            for line in res.stdout.splitlines():
                if not line.startswith("installed\t"):
                    continue
                parts = line.split("\t")
                if len(parts) < 6:
                    continue

                _, pkg, ver, prio, essential, protected = parts[:6]
                d_info = self.cached_desktop_map.get(pkg)
                if not d_info and ":" in pkg:
                    d_info = self.cached_desktop_map.get(pkg.split(":")[0])
                name = d_info[0] if d_info else pkg
                desktop_file = d_info[1] if d_info else ""
                icon = d_info[2] if d_info else pkg

                full = f"{name} {pkg}".lower()
                if q in full:
                    is_sys = (
                        prio in ["required", "important"]
                        or essential == "yes"
                        or protected == "yes"
                        or is_system_package_name(pkg)
                        or pkg in self.cached_sys_pkgs
                    )
                    results.append({
                        "name": name,
                        "package": pkg,
                        "version": ver or "-",
                        "format": "Apt",
                        "is_system": is_sys,
                        "icon": icon,
                        "desktop_file": desktop_file,
                    })
        except Exception:
            pass
        return results

    def search_all(self, query: str) -> list[dict]:
        """Run all package searches and return unified result list."""
        if len(query.strip()) < 2:
            return []

        clean_query = query.strip()
        all_results = []
        all_results.extend(self.search_flatpak(clean_query))
        all_results.extend(self.search_snap(clean_query))
        all_results.extend(self.search_local(clean_query))
        all_results.extend(self.search_apt(clean_query))
        return all_results


def launch_application(item: dict) -> tuple[bool, str]:
    """Launch application based on package format."""
    fmt = item.get("format")
    pkg = item.get("package", "")
    desktop = item.get("desktop_file", "")
    name = item.get("name", pkg)

    # 1. Launch via desktop file if present
    if desktop and os.path.isfile(desktop):
        if shutil.which("gio"):
            subprocess.Popen(["gio", "launch", desktop], start_new_session=True)
            return True, ""
        if shutil.which("gtk-launch"):
            base = os.path.splitext(os.path.basename(desktop))[0]
            subprocess.Popen(["gtk-launch", base], start_new_session=True)
            return True, ""

    # 2. Format specific fallback launch
    if fmt == "Flatpak":
        # Check exported flatpak desktop files
        candidates = [
            f"/var/lib/flatpak/exports/share/applications/{pkg}.desktop",
            os.path.expanduser(f"~/.local/share/flatpak/exports/share/applications/{pkg}.desktop"),
        ]
        for c in candidates:
            if os.path.isfile(c) and shutil.which("gio"):
                subprocess.Popen(["gio", "launch", c], start_new_session=True)
                return True, ""
        if shutil.which("flatpak"):
            subprocess.Popen(["flatpak", "run", pkg], start_new_session=True)
            return True, ""

    elif fmt == "Snap":
        candidates = (
            glob.glob(f"/var/lib/snapd/desktop/applications/{pkg}_*.desktop")
            + glob.glob(f"/var/lib/snapd/desktop/applications/{pkg}.desktop")
        )
        for c in candidates:
            if os.path.isfile(c) and shutil.which("gio"):
                subprocess.Popen(["gio", "launch", c], start_new_session=True)
                return True, ""
        if shutil.which("snap"):
            subprocess.Popen(["snap", "run", pkg], start_new_session=True)
            return True, ""

    elif fmt in ["Local", "AppImage", "PWA"]:
        exec_cmd = item.get("exec", "")
        if exec_cmd:
            # Strip desktop field codes like %u, %F, %k
            clean_cmd = re.sub(r"\s%[a-zA-Z%]", "", exec_cmd).strip()
            if clean_cmd:
                try:
                    cmd_parts = shlex.split(clean_cmd)
                    if cmd_parts:
                        subprocess.Popen(cmd_parts, start_new_session=True)
                        return True, ""
                except Exception:
                    pass

    elif fmt == "Apt":
        # Check if desktop file was installed by dpkg
        if shutil.which("dpkg"):
            try:
                res = subprocess.run(["dpkg", "-L", pkg], capture_output=True, text=True)
                for line in res.stdout.splitlines():
                    if line.startswith("/usr/share/applications/") and line.endswith(".desktop"):
                        if os.path.isfile(line) and shutil.which("gio"):
                            subprocess.Popen(["gio", "launch", line], start_new_session=True)
                            return True, ""
            except Exception:
                pass

    return False, f"Could not launch {name}"


def _try_launch(cmd: list[str]) -> bool:
    """Helper to safely execute command in a new session."""
    try:
        subprocess.Popen(cmd, start_new_session=True)
        return True
    except Exception:
        return False


def is_store_available() -> bool:
    """Check if any supported software store application or handler is installed."""
    store_binaries = [
        "gnome-software",
        "snap-store",
        "ubuntu-app-center",
        "plasma-discover",
        "mintinstall",
        "pamac-manager",
        "io.elementary.appcenter",
    ]
    if any(shutil.which(cmd) for cmd in store_binaries):
        return True
    if shutil.which("gio") or shutil.which("xdg-open"):
        return True
    return False


def can_open_in_store(item: dict) -> bool:
    """Check whether the item format can be displayed in a software store."""
    fmt = item.get("format")
    if fmt not in ["Apt", "Snap", "Flatpak"]:
        return False
    return is_store_available()


def open_in_store(item: dict) -> tuple[bool, str]:
    """Open the application in its respective software store."""
    if not can_open_in_store(item):
        return False, "Application cannot be opened in a store"

    fmt = item.get("format")
    pkg = item.get("package", "")
    desktop = item.get("desktop_file", "")
    app_id = os.path.splitext(os.path.basename(desktop))[0] if desktop else ""

    if fmt == "Snap":
        # 1. Snap Store / Ubuntu App Center
        if shutil.which("snap-store") and _try_launch(["snap-store", f"snap://{pkg}"]):
            return True, ""
        if shutil.which("ubuntu-app-center") and _try_launch(["ubuntu-app-center", f"snap://{pkg}"]):
            return True, ""
        # 2. GNOME Software
        if shutil.which("gnome-software") and _try_launch(["gnome-software", f"--details={pkg}"]):
            return True, ""
        # 3. GIO / xdg-open URL handler
        if shutil.which("gio") and _try_launch(["gio", "open", f"snap://{pkg}"]):
            return True, ""
        if shutil.which("xdg-open") and _try_launch(["xdg-open", f"snap://{pkg}"]):
            return True, ""
        # 4. KDE Discover
        if shutil.which("plasma-discover") and _try_launch(["plasma-discover", "--application", pkg]):
            return True, ""

    elif fmt == "Flatpak":
        # 1. GNOME Software
        if shutil.which("gnome-software") and _try_launch(["gnome-software", f"--details={pkg}"]):
            return True, ""
        # 2. KDE Discover
        if shutil.which("plasma-discover") and _try_launch(["plasma-discover", "--application", pkg]):
            return True, ""
        # 3. Linux Mint Software Manager
        if shutil.which("mintinstall") and _try_launch(["mintinstall", pkg]):
            return True, ""
        # 4. Elementary AppCenter
        if shutil.which("io.elementary.appcenter") and _try_launch(["io.elementary.appcenter", f"appstream://{pkg}"]):
            return True, ""
        # 5. GIO / xdg-open URL handler
        if shutil.which("gio") and _try_launch(["gio", "open", f"appstream://{pkg}"]):
            return True, ""
        if shutil.which("xdg-open") and _try_launch(["xdg-open", f"appstream://{pkg}"]):
            return True, ""

    elif fmt == "Apt":
        # 1. Linux Mint Software Manager
        if shutil.which("mintinstall") and _try_launch(["mintinstall", pkg]):
            return True, ""
        # 2. GNOME Software
        if shutil.which("gnome-software") and _try_launch(["gnome-software", f"--details-pkg={pkg}"]):
            return True, ""
        # 3. Snap Store / App Center
        if shutil.which("snap-store") and _try_launch(["snap-store", f"snap://{pkg}"]):
            return True, ""
        # 4. KDE Discover
        if shutil.which("plasma-discover") and _try_launch(["plasma-discover", "--application", pkg]):
            return True, ""
        # 5. GIO / xdg-open URL handler
        stream_id = app_id if app_id else pkg
        if shutil.which("gio") and _try_launch(["gio", "open", f"appstream://{stream_id}"]):
            return True, ""
        if shutil.which("xdg-open") and _try_launch(["xdg-open", f"apt://{pkg}"]):
            return True, ""

    return False, f"Could not open {pkg} in software store"


def uninstall_application(item: dict, i18n) -> tuple[bool, str]:
    """Perform application uninstallation using pkexec (graphical auth) or terminal fallback."""
    fmt = item.get("format")
    pkg = item.get("package", "")
    name = item.get("name", pkg)

    if item.get("is_system") or (fmt == "Apt" and is_system_package_name(pkg)):
        return False, i18n.get("system_uninstall_disabled")

    if fmt in ["Apt", "Snap", "Flatpak"]:
        if not is_valid_package_name(pkg, fmt):
            return False, f"Invalid package name: {pkg}"

    has_pkexec = shutil.which("pkexec") is not None

    if fmt in ["Local", "AppImage", "PWA"]:
        desktop_file = item.get("desktop_file", "")
        if desktop_file and os.path.isfile(desktop_file):
            is_link = os.path.islink(desktop_file)
            if (is_link or os.access(desktop_file, os.W_OK)) and os.access(os.path.dirname(desktop_file), os.W_OK):
                try:
                    info = parse_desktop_file(desktop_file) if not is_link else {}
                    exec_line = info.get("exec", "")
                    os.remove(desktop_file)
                    if exec_line:
                        try:
                            parts = shlex.split(exec_line)
                            raw_bin = parts[0] if parts else ""
                        except Exception:
                            raw_bin = exec_line.split()[0] if exec_line.split() else ""

                        clean_exec = os.path.abspath(os.path.expanduser(raw_bin))
                        if is_safe_user_app_dir(clean_exec) and os.path.isdir(clean_exec):
                            shutil.rmtree(clean_exec, ignore_errors=True)
                        elif clean_exec.lower().endswith(".appimage") and os.path.isfile(clean_exec):
                            if clean_exec.startswith(os.path.expanduser("~")):
                                os.remove(clean_exec)

                        symlink = os.path.expanduser(f"~/.local/bin/{os.path.basename(clean_exec)}")
                        if os.path.islink(symlink):
                            os.remove(symlink)
                    return True, i18n.get("uninstall_success", name=name)
                except Exception as e:
                    return False, str(e)
            elif has_pkexec and is_safe_system_desktop_path(desktop_file):
                real_desktop = os.path.realpath(desktop_file)
                cmd = ["pkexec", "rm", "-f", "--", real_desktop]
                try:
                    res = subprocess.run(cmd, capture_output=True, text=True)
                    if res.returncode == 0:
                        return True, i18n.get("uninstall_success", name=name)
                    elif res.returncode in [126, 127]:
                        return False, i18n.get("uninstall_cancelled")
                    else:
                        return False, res.stderr.strip() or f"Exit code {res.returncode}"
                except Exception as e:
                    return False, str(e)
            elif has_pkexec:
                return False, "Unauthorized desktop file path"

    if has_pkexec:
        cmd = []
        if fmt == "Snap":
            cmd = ["pkexec", "snap", "remove", "--", pkg]
        elif fmt == "Apt":
            cmd = ["pkexec", "apt-get", "remove", "-y", "--", pkg]
        elif fmt == "Flatpak":
            cmd = ["flatpak", "uninstall", "-y", "--", pkg]

        if cmd:
            try:
                res = subprocess.run(cmd, capture_output=True, text=True)
                if res.returncode == 0:
                    return True, i18n.get("uninstall_success", name=name)
                elif res.returncode in [126, 127]:
                    return False, i18n.get("uninstall_cancelled")
                else:
                    err = res.stderr.strip() or res.stdout.strip() or f"Exit code {res.returncode}"
                    return False, i18n.get("uninstall_error", name=name, err=err)
            except Exception as e:
                return False, str(e)

    # Terminal fallback if pkexec not available
    term_bin, style = find_terminal_emulator()
    if not term_bin:
        return False, i18n.get("no_terminal")

    exit_prompt = i18n.get("terminal_exit")
    safe_pkg = shlex.quote(pkg)
    safe_prompt = shlex.quote(exit_prompt)
    bash_cmd = ""
    if fmt == "Snap":
        bash_cmd = f"sudo snap remove -- {safe_pkg}; echo ''; read -p {safe_prompt}"
    elif fmt == "Apt":
        bash_cmd = f"sudo apt remove -- {safe_pkg}; echo ''; read -p {safe_prompt}"
    elif fmt == "Flatpak":
        bash_cmd = f"flatpak uninstall -- {safe_pkg}; echo ''; read -p {safe_prompt}"

    if not bash_cmd:
        return False, "Unknown format for uninstallation"

    try:
        if style in ["gnome", "konsole"]:
            subprocess.Popen([term_bin, "--", "bash", "-c", bash_cmd], start_new_session=True)
        else:
            subprocess.Popen([term_bin, "-e", "bash", "-c", bash_cmd], start_new_session=True)
        return True, ""
    except Exception as e:
        return False, str(e)
