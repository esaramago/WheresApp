#!/usr/bin/env python3
# GTK 4 / Libadwaita graphical interface for WheresApp
import os
import threading
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk

from engine import SearchEngine, launch_application, uninstall_application
from i18n import I18n


def create_app_icon(icon_name: str) -> Gtk.Widget:
    """Create an icon image widget from an icon name or file path."""
    if not icon_name:
        img = Gtk.Image.new_from_icon_name("application-x-executable-symbolic")
        img.set_icon_size(Gtk.IconSize.LARGE)
        return img

    if os.path.isabs(icon_name) and os.path.isfile(icon_name):
        return Gtk.Image.new_from_file(icon_name)

    # Check /usr/share/pixmaps for image files matching the icon name
    for ext in [".png", ".svg"]:
        candidate = os.path.join("/usr/share/pixmaps", icon_name + ext)
        if os.path.isfile(candidate):
            return Gtk.Image.new_from_file(candidate)

    img = Gtk.Image.new_from_icon_name(icon_name)
    img.set_icon_size(Gtk.IconSize.LARGE)
    return img


class WheresAppWindow(Adw.ApplicationWindow):
    """Main application window using Libadwaita widgets."""

    def __init__(self, app: Adw.Application, i18n: I18n, initial_query: str = ""):
        super().__init__(application=app, title=i18n.get("title"))
        self.i18n = i18n
        self.engine = SearchEngine()
        self.search_timer_id: int | None = None
        self.current_search_id: int = 0

        self.set_default_size(800, 600)
        self.set_icon_name("wheresapp")

        # Top-level toast overlay for user action feedback
        self.toast_overlay = Adw.ToastOverlay()
        self.set_content(self.toast_overlay)

        # Main vertical container
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.toast_overlay.set_child(main_box)

        # Header bar
        header_bar = Adw.HeaderBar()
        main_box.append(header_bar)

        # Search bar container
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        search_box.set_margin_top(12)
        search_box.set_margin_bottom(12)
        search_box.set_margin_start(16)
        search_box.set_margin_end(16)

        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text(self.i18n.get("search_prompt"))
        self.search_entry.set_hexpand(True)
        self.search_entry.connect("search-changed", self._on_search_changed)
        self.search_entry.connect("activate", self._on_search_activated)
        search_box.append(self.search_entry)

        self.spinner = Gtk.Spinner()
        self.spinner.set_visible(False)
        search_box.append(self.spinner)

        main_box.append(search_box)

        # View stack: empty state, not found state, results list
        self.stack = Gtk.Stack()
        self.stack.set_vexpand(True)
        self.stack.set_hexpand(True)
        main_box.append(self.stack)

        # 1. Initial empty search page
        self.empty_page = Adw.StatusPage()
        self.empty_page.set_icon_name("system-search-symbolic")
        self.empty_page.set_title(self.i18n.get("empty_title"))
        self.empty_page.set_description(self.i18n.get("empty_desc"))
        self.stack.add_named(self.empty_page, "empty")

        # 2. No results page
        self.not_found_page = Adw.StatusPage()
        self.not_found_page.set_icon_name("edit-find-symbolic")
        self.not_found_page.set_title(self.i18n.get("not_found_title"))
        self.stack.add_named(self.not_found_page, "not_found")

        # 3. Results list inside a scrolled window
        self.scrolled_window = Gtk.ScrolledWindow()
        self.scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.list_box.add_css_class("boxed-list")
        self.list_box.set_margin_start(16)
        self.list_box.set_margin_end(16)
        self.list_box.set_margin_bottom(16)

        self.scrolled_window.set_child(self.list_box)
        self.stack.add_named(self.scrolled_window, "results")

        self.stack.set_visible_child_name("empty")

        # Apply initial query if provided from command line
        if initial_query:
            self.search_entry.set_text(initial_query)

    def show_toast(self, message: str):
        """Display an informational toast notification."""
        toast = Adw.Toast.new(message)
        toast.set_timeout(3)
        self.toast_overlay.add_toast(toast)

    def _on_search_changed(self, entry: Gtk.SearchEntry):
        """Handle search text input with debounce timing."""
        if self.search_timer_id is not None:
            GLib.source_remove(self.search_timer_id)
            self.search_timer_id = None

        text = entry.get_text().strip()
        self.current_search_id += 1

        if len(text) < 2:
            self.spinner.stop()
            self.spinner.set_visible(False)
            self.stack.set_visible_child_name("empty")
            return

        self.spinner.set_visible(True)
        self.spinner.start()

        # Debounce search execution by 200 milliseconds
        self.search_timer_id = GLib.timeout_add(
            200, self._start_search_thread, text, self.current_search_id
        )

    def _on_search_activated(self, entry: Gtk.SearchEntry):
        """Trigger immediate search when Enter is pressed in search entry."""
        if self.search_timer_id is not None:
            GLib.source_remove(self.search_timer_id)
            self.search_timer_id = None

        text = entry.get_text().strip()
        if len(text) >= 2:
            self.current_search_id += 1
            self.spinner.set_visible(True)
            self.spinner.start()
            self._start_search_thread(text, self.current_search_id)

    def _start_search_thread(self, query: str, search_id: int) -> bool:
        """Start worker thread to execute package queries in background."""
        self.search_timer_id = None
        thread = threading.Thread(
            target=self._run_search,
            args=(query, search_id),
            daemon=True,
        )
        thread.start()
        return False  # Do not repeat GLib timer

    def _run_search(self, query: str, search_id: int):
        """Worker thread entry point for package queries."""
        results = self.engine.search_all(query)
        GLib.idle_add(self._on_search_completed, results, query, search_id)

    def _on_search_completed(self, results: list[dict], query: str, search_id: int) -> bool:
        """Update interface with search results on the main GTK thread."""
        if search_id != self.current_search_id:
            return False

        self.spinner.stop()
        self.spinner.set_visible(False)

        if not results:
            desc = self.i18n.get("not_found_desc", query=query)
            self.not_found_page.set_description(desc)
            self.stack.set_visible_child_name("not_found")
            return False

        # Clear existing rows
        while True:
            row = self.list_box.get_first_child()
            if row is None:
                break
            self.list_box.remove(row)

        # Build row for each search result
        for item in results:
            action_row = self._create_result_row(item)
            self.list_box.append(action_row)

        self.stack.set_visible_child_name("results")
        return False

    def _create_result_row(self, item: dict) -> Adw.ActionRow:
        """Construct an action row widget for a search result item."""
        row = Adw.ActionRow()
        row.set_title(item["name"])

        # Subtitle: format, package name, version
        ver_text = f"v{item['version']}" if item["version"] != "-" else ""
        subtitle_parts = [item["format"], item["package"]]
        if ver_text:
            subtitle_parts.append(ver_text)
        row.set_subtitle(" • ".join(subtitle_parts))

        # Application icon prefix
        icon_widget = create_app_icon(item.get("icon", ""))
        row.add_prefix(icon_widget)

        # System package warning badge
        if item.get("is_system"):
            sys_badge = Gtk.Label(label=self.i18n.get("system_badge"))
            sys_badge.add_css_class("error")
            sys_badge.set_tooltip_text(self.i18n.get("system_tooltip"))
            row.add_suffix(sys_badge)

        # Launch application button
        btn_open = Gtk.Button.new_from_icon_name("media-playback-start-symbolic")
        btn_open.add_css_class("flat")
        btn_open.set_tooltip_text(self.i18n.get("btn_open"))
        btn_open.connect("clicked", lambda _b, it=item: self._on_launch_clicked(it))
        row.add_suffix(btn_open)

        # Uninstall application button
        btn_uninstall = Gtk.Button.new_from_icon_name("user-trash-symbolic")
        btn_uninstall.add_css_class("flat")
        btn_uninstall.add_css_class("destructive-action")
        btn_uninstall.set_tooltip_text(self.i18n.get("btn_uninstall"))
        btn_uninstall.connect("clicked", lambda _b, it=item: self._on_uninstall_clicked(it))
        row.add_suffix(btn_uninstall)

        return row

    def _on_launch_clicked(self, item: dict):
        """Handle application launch request."""
        success, err = launch_application(item)
        if success:
            self.show_toast(self.i18n.get("launching_app", name=item["name"]))
        else:
            self.show_toast(self.i18n.get("launch_failed", name=item["name"]))

    def _on_uninstall_clicked(self, item: dict):
        """Display confirmation dialog before starting uninstallation."""
        heading = self.i18n.get("confirm_title")
        if item.get("name") and item["name"] != item["package"] and item["name"] != "-":
            body = self.i18n.get(
                "confirm_msg_app",
                name=item["name"],
                pkg=item["package"],
                ver=item["version"],
                fmt=item["format"],
            )
        else:
            body = self.i18n.get(
                "confirm_msg_pkg",
                pkg=item["package"],
                ver=item["version"],
                fmt=item["format"],
            )

        if item.get("is_system"):
            body = f"{self.i18n.get('confirm_system_warn')}\n\n{body}"

        dialog = Adw.AlertDialog(heading=heading, body=body)
        dialog.add_response("cancel", self.i18n.get("btn_cancel"))
        dialog.add_response("uninstall", self.i18n.get("btn_confirm_yes"))
        dialog.set_response_appearance("uninstall", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")

        dialog.choose(self, None, self._on_dialog_response, item)

    def _on_dialog_response(self, dialog: Adw.AlertDialog, result, item: dict):
        """Process response from uninstallation confirmation dialog."""
        response = dialog.choose_finish(result)
        if response == "uninstall":
            success, err = uninstall_application(item, self.i18n)
            if success:
                self.show_toast(self.i18n.get("uninstall_started"))
            else:
                self.show_toast(err or "Failed to start uninstaller")
