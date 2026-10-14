#!/usr/bin/env python3
# GTK 4 / Libadwaita graphical interface for WheresApp with Card Grid layout
import os
import threading
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk, Pango

from engine import SearchEngine, launch_application, uninstall_application
from i18n import I18n


def create_app_icon(icon_name: str, pixel_size: int = 48) -> Gtk.Widget:
    """Create an icon image widget with specified pixel size."""
    if not icon_name:
        img = Gtk.Image.new_from_icon_name("application-x-executable-symbolic")
        img.set_pixel_size(pixel_size)
        return img

    if os.path.isabs(icon_name) and os.path.isfile(icon_name):
        img = Gtk.Image.new_from_file(icon_name)
        img.set_pixel_size(pixel_size)
        return img

    # Check /usr/share/pixmaps for image files matching the icon name
    for ext in [".png", ".svg"]:
        candidate = os.path.join("/usr/share/pixmaps", icon_name + ext)
        if os.path.isfile(candidate):
            img = Gtk.Image.new_from_file(candidate)
            img.set_pixel_size(pixel_size)
            return img

    img = Gtk.Image.new_from_icon_name(icon_name)
    img.set_pixel_size(pixel_size)
    return img


class WheresAppWindow(Adw.ApplicationWindow):
    """Main application window using Libadwaita widgets with Card Grid layout."""

    def __init__(self, app: Adw.Application, i18n: I18n, initial_query: str = ""):
        super().__init__(application=app, title=i18n.get("title"))
        self.i18n = i18n
        self.engine = SearchEngine()
        self.search_timer_id: int | None = None
        self.current_search_id: int = 0

        self.set_default_size(880, 620)
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

        # View stack: empty state, not found state, results card grid
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

        # 3. Results card grid inside a scrolled window
        self.scrolled_window = Gtk.ScrolledWindow()
        self.scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.flow_box = Gtk.FlowBox()
        self.flow_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flow_box.set_homogeneous(True)
        self.flow_box.set_column_spacing(12)
        self.flow_box.set_row_spacing(12)
        self.flow_box.set_min_children_per_line(1)
        self.flow_box.set_max_children_per_line(4)
        self.flow_box.set_valign(Gtk.Align.START)
        self.flow_box.set_margin_start(16)
        self.flow_box.set_margin_end(16)
        self.flow_box.set_margin_bottom(16)

        self.scrolled_window.set_child(self.flow_box)
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
        """Update interface with search result cards on the main GTK thread."""
        if search_id != self.current_search_id:
            return False

        self.spinner.stop()
        self.spinner.set_visible(False)

        if not results:
            desc = self.i18n.get("not_found_desc", query=query)
            self.not_found_page.set_description(desc)
            self.stack.set_visible_child_name("not_found")
            return False

        # Clear existing cards
        while True:
            child = self.flow_box.get_first_child()
            if child is None:
                break
            self.flow_box.remove(child)

        # Build card widget for each search result
        for item in results:
            card_child = self._create_card_widget(item)
            self.flow_box.append(card_child)

        self.stack.set_visible_child_name("results")
        return False

    def _create_card_widget(self, item: dict) -> Gtk.FlowBoxChild:
        """Construct a responsive card widget for a search result item."""
        card_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card_box.add_css_class("card")
        card_box.set_size_request(260, -1)

        # Inner container with margins for padding
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        inner.set_margin_top(12)
        inner.set_margin_bottom(12)
        inner.set_margin_start(12)
        inner.set_margin_end(12)
        card_box.append(inner)

        # Top row: application icon on the left, name & package in the middle, badges on the right
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        icon_widget = create_app_icon(item.get("icon", ""), pixel_size=48)
        icon_widget.set_valign(Gtk.Align.CENTER)
        header.append(icon_widget)

        # Application Name and Package info to the right of the icon
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        info_box.set_valign(Gtk.Align.CENTER)
        info_box.set_hexpand(True)

        title_label = Gtk.Label(label=item["name"])
        title_label.add_css_class("heading")
        title_label.set_halign(Gtk.Align.START)
        title_label.set_ellipsize(Pango.EllipsizeMode.END)
        title_label.set_tooltip_text(item["name"])
        info_box.append(title_label)

        ver_text = f"v{item['version']}" if item["version"] != "-" else ""
        sub_text = f"{item['package']} {ver_text}".strip()
        pkg_label = Gtk.Label(label=sub_text)
        pkg_label.add_css_class("dim-label")
        pkg_label.add_css_class("caption")
        pkg_label.set_halign(Gtk.Align.START)
        pkg_label.set_ellipsize(Pango.EllipsizeMode.END)
        pkg_label.set_tooltip_text(sub_text)
        info_box.append(pkg_label)

        header.append(info_box)

        # Badges box on the right
        badge_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        badge_box.set_valign(Gtk.Align.START)
        badge_box.set_halign(Gtk.Align.END)

        # Format tag badge
        fmt_label = Gtk.Label(label=item["format"])
        fmt_label.add_css_class("caption")
        fmt_label.add_css_class("accent")
        badge_box.append(fmt_label)

        # System package warning badge
        if item.get("is_system"):
            sys_badge = Gtk.Label(label=self.i18n.get("system_badge"))
            sys_badge.add_css_class("caption")
            sys_badge.add_css_class("error")
            sys_badge.set_tooltip_text(self.i18n.get("system_tooltip"))
            badge_box.append(sys_badge)

        header.append(badge_box)
        inner.append(header)

        # Spacer to push action buttons to card bottom
        spacer = Gtk.Box()
        spacer.set_vexpand(True)
        inner.append(spacer)

        # Action buttons row
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_box.set_margin_top(6)

        # Open button with icon and label
        btn_open = Gtk.Button()
        btn_open_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_open_box.set_halign(Gtk.Align.CENTER)
        btn_open_box.append(Gtk.Image.new_from_icon_name("external-link-symbolic"))
        btn_open_box.append(Gtk.Label(label=self.i18n.get("btn_open")))
        btn_open.set_child(btn_open_box)
        btn_open.set_hexpand(True)
        btn_open.set_tooltip_text(self.i18n.get("btn_open"))
        btn_open.connect("clicked", lambda _b, it=item: self._on_launch_clicked(it))
        btn_box.append(btn_open)

        # Uninstall button with icon and label
        btn_uninstall = Gtk.Button()
        btn_uninstall_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_uninstall_box.set_halign(Gtk.Align.CENTER)
        btn_uninstall_box.append(Gtk.Image.new_from_icon_name("user-trash-symbolic"))
        btn_uninstall_box.append(Gtk.Label(label=self.i18n.get("btn_uninstall")))
        btn_uninstall.set_child(btn_uninstall_box)
        btn_uninstall.add_css_class("destructive-action")
        btn_uninstall.set_hexpand(True)
        btn_uninstall.set_tooltip_text(self.i18n.get("btn_uninstall"))
        btn_uninstall.connect("clicked", lambda _b, it=item: self._on_uninstall_clicked(it))
        btn_box.append(btn_uninstall)

        inner.append(btn_box)

        # FlowBoxChild container
        child = Gtk.FlowBoxChild()
        child.set_child(card_box)
        child.set_focusable(False)
        return child

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
