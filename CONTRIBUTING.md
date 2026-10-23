# Contributing to WheresApp

Thank you for your interest in contributing to **WheresApp**! Contributions from the community help make this project better for everyone.

This document provides guidelines and instructions for contributing to the codebase.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Setting Up the Repository](#setting-up-the-repository)
- [Project Structure](#project-structure)
- [Development Workflow](#development-workflow)
  - [Running the App Locally](#running-the-app-locally)
  - [Running Tests](#running-tests)
  - [Code Style and Comments](#code-style-and-comments)
  - [Adding or Updating Translations](#adding-or-updating-translations)
  - [Building the Debian Package](#building-the-debian-package)
- [Git and Commit Guidelines](#git-and-commit-guidelines)
- [Submitting a Pull Request](#submitting-a-pull-request)
- [Reporting Issues](#reporting-issues)

---

## Code of Conduct

Please be respectful, collaborative, and considerate of others when interacting with this repository, reporting issues, or reviewing pull requests.

---

## Getting Started

### Prerequisites

WheresApp is written in Python 3 using GTK 4 and Libadwaita (PyGObject). Ensure the following dependencies are installed:

```bash
sudo apt update
sudo apt install python3 python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 dpkg
```

Optional dependencies for testing specific packaging formats:
- `snapd` (for Snap detection and removal)
- `flatpak` (for Flatpak detection and removal)

### Setting Up the Repository

1. Fork the repository on GitHub.
2. Clone your fork locally:
   ```bash
   git clone https://github.com/<your-username>/wheresapp.git
   cd wheresapp
   ```
3. Create a new branch for your feature or bug fix:
   ```bash
   git checkout -b feat/your-feature-name
   # or
   git checkout -b fix/your-bug-fix
   ```

---

## Project Structure

```
wheresapp/
├── DEBIAN/
│   └── control                     # Debian package metadata and dependencies
├── build.sh                        # Automated Debian package builder (.deb)
├── tests/
│   └── test_engine.py              # Unit tests for search engine, parsers, and i18n
├── usr/
│   ├── local/
│   │   └── bin/
│   │       └── wheresapp           # Main executable launcher
│   └── share/
│       ├── applications/
│       │   └── wheresapp.desktop   # Desktop launcher entry
│       ├── metainfo/
│       │   └── com.github.esaramago.wheresapp.metainfo.xml
│       ├── pixmaps/                # Application and format icons
│       └── wheresapp/
│           ├── engine.py           # Core logic (search, desktop parser, uninstallation)
│           ├── i18n.py             # Multi-language translation engine
│           └── ui.py               # GTK 4 / Libadwaita user interface
```

---

## Development Workflow

### Running the App Locally

You can run WheresApp directly without installing it:

```bash
# Ensure executable permissions
chmod +x usr/local/bin/wheresapp

# Launch with default system locale
./usr/local/bin/wheresapp

# Launch with a specific locale
./usr/local/bin/wheresapp --lang en
./usr/local/bin/wheresapp --lang pt
```

### Running Tests

Before committing changes, run the test suite to ensure all unit tests pass:

```bash
python3 -m unittest discover -s tests
```

If you add new functionality to `engine.py` or `i18n.py`, remember to add corresponding unit tests in `tests/test_engine.py`.

### Code Style and Comments

- **Language for Comments & Code**: All code comments, docstrings, variable names, and commit messages **must be in English**.
- **Python Conventions**: Follow [PEP 8](https://peps.python.org/pep-0008/) style guidelines.
- **Safety**: Ensure operations handling file paths, package uninstalls, and terminal commands validate inputs and avoid path traversal vulnerabilities or command injection.

### Adding or Updating Translations

Translations are managed in `usr/share/wheresapp/i18n.py`.
- Key-value pairs are stored in the `TRANSLATIONS` dictionary.
- Currently supported locales include `en-GB` (`en`) and `pt-PT` (`pt`).
- When introducing a new UI string, add entries for all supported languages.

### Building the Debian Package

To verify that the packaging process succeeds without errors:

```bash
./build.sh
```

This creates a `wheresapp_<version>.deb` package in the root directory.

---

## Git and Commit Guidelines

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

- `feat:` A new feature (e.g., `feat(engine): add flatpak store integration`)
- `fix:` A bug fix (e.g., `fix(ui): prevent UI freeze during search`)
- `docs:` Documentation-only changes (e.g., `docs: update CONTRIBUTING.md`)
- `style:` Formatting, missing semi-colons, etc. (no code changes)
- `refactor:` Code change that neither fixes a bug nor adds a feature
- `test:` Adding or updating tests
- `chore:` Maintenance tasks, dependency updates, packaging fixes

Commit messages must be clear, concise, and written in English.

---

## Submitting a Pull Request

1. Push your branch to your GitHub fork:
   ```bash
   git push origin feat/your-feature-name
   ```
2. Open a Pull Request (PR) against the `main` branch of the upstream repository.
3. PR Checklist:
   - [ ] Branch is up-to-date with upstream `main`.
   - [ ] All tests pass (`python3 -m unittest discover -s tests`).
   - [ ] Code comments and commit messages are in English.
   - [ ] New features include relevant unit tests.
   - [ ] Package build succeeds (`./build.sh`).
4. Describe your changes clearly in the PR description, referencing any related issue numbers (e.g., `Fixes #12`).

---

## Reporting Issues

If you find a bug or have a feature suggestion, please open an issue on GitHub:
- **Bug Reports**: Include your OS/distribution version, desktop environment, steps to reproduce, and any terminal output or error tracebacks.
- **Feature Requests**: Explain the proposed feature and why it would be beneficial to users.
