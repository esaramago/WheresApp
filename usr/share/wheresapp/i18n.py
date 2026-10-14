#!/usr/bin/env python3
# Localization support for WheresApp
import os
import sys

# Built-in translation dictionaries for English (en-GB) and Portuguese (pt-PT)
TRANSLATIONS = {
    "en-GB": {
        "title": "WheresApp",
        "search_prompt": "Application name or package...",
        "search_placeholder": "Type at least 2 characters to search...",
        "empty_title": "Search Applications",
        "empty_desc": "Find, open, or uninstall APT, Snap, Flatpak, AppImage, and PWA applications.",
        "not_found_title": "No Applications Found",
        "not_found_desc": "No packages match '{query}'.",
        "col_app": "Application",
        "col_pkg": "Package",
        "col_ver": "Version",
        "col_format": "Format",
        "col_system": "System",
        "system_badge": "🔴 System",
        "system_tooltip": "System application — removal may cause system instability",
        "btn_open": "Open",
        "btn_uninstall": "Uninstall",
        "btn_cancel": "Cancel",
        "confirm_title": "Confirm Uninstallation",
        "confirm_system_warn": "⚠️ WARNING: This is a system application!\nUninstalling it may damage or make the system unstable.",
        "confirm_msg_app": "Are you sure you want to uninstall '{name}' (package: {pkg}, v{ver}) [{fmt}]?\nThis action may remove associated user data.",
        "confirm_msg_pkg": "Are you sure you want to uninstall package '{pkg}' (v{ver}) [{fmt}]?\nThis action may remove associated user data.",
        "btn_confirm_yes": "Uninstall",
        "terminal_exit": "Finished! Press Enter to exit...",
        "terminal_uninstall_title": "=== Application Uninstallation ===",
        "terminal_confirm_delete": "Do you want to delete these files? (y/N): ",
        "terminal_file_removed": "Removed:",
        "terminal_uninstall_done": "Application successfully removed.",
        "terminal_uninstall_cancel": "Uninstallation cancelled.",
        "launching_app": "Launching {name}...",
        "launch_failed": "Could not launch application '{name}'.",
        "uninstall_started": "Uninstallation launched in terminal.",
        "no_terminal": "No supported terminal emulator found.",
    },
    "pt-PT": {
        "title": "WheresApp",
        "search_prompt": "Nome da aplicação ou pacote...",
        "search_placeholder": "Escreva pelo menos 2 caracteres para pesquisar...",
        "empty_title": "Procurar Aplicações",
        "empty_desc": "Procurar, abrir ou desinstalar aplicações APT, Snap, Flatpak, AppImage e PWA.",
        "not_found_title": "Nenhuma Aplicação Encontrada",
        "not_found_desc": "Nenhum pacote corresponde a '{query}'.",
        "col_app": "Aplicação",
        "col_pkg": "Pacote",
        "col_ver": "Versão",
        "col_format": "Formato",
        "col_system": "Sistema",
        "system_badge": "🔴 Sistema",
        "system_tooltip": "Aplicação de sistema — a remoção pode tornar o sistema instável",
        "btn_open": "Abrir",
        "btn_uninstall": "Desinstalar",
        "btn_cancel": "Cancelar",
        "confirm_title": "Confirmar Desinstalação",
        "confirm_system_warn": "⚠️ ATENÇÃO: Esta é uma aplicação de sistema!\nA sua desinstalação pode danificar ou tornar o sistema instável.",
        "confirm_msg_app": "Tem a certeza de que deseja desinstalar '{name}' (pacote: {pkg}, v{ver}) [{fmt}]?\nEsta ação pode remover dados associados.",
        "confirm_msg_pkg": "Tem a certeza de que deseja desinstalar o pacote '{pkg}' (v{ver}) [{fmt}]?\nEsta ação pode remover dados associados.",
        "btn_confirm_yes": "Desinstalar",
        "terminal_exit": "Concluído! Pressione Enter para sair...",
        "terminal_uninstall_title": "=== Desinstalação da Aplicação ===",
        "terminal_confirm_delete": "Deseja remover estes ficheiros? (s/N): ",
        "terminal_file_removed": "Removido:",
        "terminal_uninstall_done": "Aplicação removida com sucesso.",
        "terminal_uninstall_cancel": "Desinstalação cancelada.",
        "launching_app": "A iniciar {name}...",
        "launch_failed": "Não foi possível iniciar a aplicação '{name}'.",
        "uninstall_started": "Desinstalação iniciada no terminal.",
        "no_terminal": "Nenhum emulador de terminal suportado foi encontrado.",
    }
}


def get_active_locale(requested_lang: str | None = None) -> str:
    """Determine the active language code (en-GB or pt-PT)."""
    target = requested_lang or os.environ.get("APP_LANG") or os.environ.get("LC_ALL") or os.environ.get("LC_MESSAGES") or os.environ.get("LANG") or "en_GB"
    target = target.lower()
    if target.startswith("pt"):
        return "pt-PT"
    return "en-GB"


class I18n:
    """Translation helper class."""

    def __init__(self, requested_lang: str | None = None):
        self.locale = get_active_locale(requested_lang)
        self.strings = TRANSLATIONS.get(self.locale, TRANSLATIONS["en-GB"])

    def get(self, key: str, **kwargs) -> str:
        """Retrieve translated string with optional formatting parameters."""
        raw = self.strings.get(key, TRANSLATIONS["en-GB"].get(key, key))
        if kwargs:
            try:
                return raw.format(**kwargs)
            except Exception:
                return raw
        return raw
