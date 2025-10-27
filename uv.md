## 🛠️ What is uv?

* uv is a modern Python package + project manager (written in Rust) aiming to unify tools like `pip`, `pipx`, `virtualenv`, `pip-tools`, `pyenv`, etc. ([Astral][2])
* It offers faster dependency resolution, lockfile support, environment management, and tool installation. ([Astral][2])
* Its “pip interface” means you often run `uv pip install <pkg>` instead of `pip install <pkg>`. ([Astral Docs][3])

---

## ✅ Installation

You have multiple ways to install uv. Use the method that best fits your OS and preferences.

### 📦 Standalone installer (recommended for many users)

* **Linux / macOS**

  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

* **Windows (PowerShell)**

  ```powershell
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```


---

### 📦 Alternative install methods

* **From PyPI**

  ```bash
  pip install uv
  ```

  Or using pipx if you prefer isolating it:

  ```bash
  pipx install uv
  ```

  (Note: when installed by pip/pipx, self-update via `uv self update` may be disabled; to upgrade, use pip or pipx update) ([Astral Docs][1])

* **Via system package manager**
  Depending on your OS, uv might be available (e.g. Homebrew on macOS) ([Astral Docs][1])

---

## 🧰 Initial setup & usage

Once uv is installed, here’s how you can get started in a Python project.

### 1. Initialize a uv project

In your project folder:

```bash
uv init
```

This generates:

* `pyproject.toml`
* `.python-version` (to pin Python version)
* `uv.lock` (for locked dependencies)
* `.gitignore`
* Starter files, etc. ([Astral Docs][3])

### 2. Managing environments & dependencies

* To create a venv (virtual environment) inside your project:

  ```bash
  uv venv
  ```

* To install dependencies:

  ```bash
  uv pip install flask
  uv pip install -r requirements.txt
  uv pip install -e .
  ```

* To sync environment with lockfile:

  ```bash
  uv sync
  ```

* To update lockfile or upgrade:

  ```bash
  uv lock
  uv lock --upgrade
  ```

* To remove a dependency:

  ```bash
  uv remove some-package
  ```

### 3. Python version management

uv can also install or manage Python versions directly:

```bash
uv python install 3.11
uv python list
uv python pin 3.11
```
