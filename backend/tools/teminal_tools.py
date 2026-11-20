
"""
Terminal Toolkit for LangChain Agents
Supports:
- Windows CMD
- Windows PowerShell
- PowerShell Core (pwsh on Linux/macOS)
- Workspace file operations

Install:
    pip install -U langchain langchain-core

Environment:
    TERMINAL_WORKSPACE = project workspace path
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Optional

from langchain_core.tools import tool


# =====================================================
# CONFIGURATION
# =====================================================

WORKSPACE_ROOT = Path(
    os.getenv("TERMINAL_WORKSPACE", str(Path.cwd()))
).expanduser().resolve()

WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)

CURRENT_DIRECTORY = WORKSPACE_ROOT

COMMAND_TIMEOUT = 60
MAX_OUTPUT_LENGTH = 12000
MAX_FILE_SIZE = 1_000_000


# =====================================================
# HELPERS
# =====================================================

def _truncate(text: str) -> str:
    if len(text) > MAX_OUTPUT_LENGTH:
        return text[:MAX_OUTPUT_LENGTH] + "\n\n[OUTPUT TRUNCATED]"
    return text


def _resolve_path(path: str) -> Path:
    """Resolve a path and ensure it remains inside workspace."""

    target = Path(path).expanduser()

    if not target.is_absolute():
        target = CURRENT_DIRECTORY / target

    target = target.resolve()

    try:
        target.relative_to(WORKSPACE_ROOT)
    except ValueError:
        raise ValueError(
            f"Ruxsat berilmagan yo'l. Workspace: {WORKSPACE_ROOT}"
        )

    return target


def _get_powershell() -> Optional[str]:
    """Find available PowerShell executable."""

    import shutil

    if os.name == "nt":
        return shutil.which("powershell") or shutil.which("pwsh")

    return shutil.which("pwsh")


def _check_dangerous_command(command: str) -> Optional[str]:
    """
    Basic protection against common destructive commands.
    This is NOT a security sandbox.
    """

    patterns = [
        r"\bformat\s+[a-z]:",
        r"\bshutdown\b",
        r"\bdiskpart\b",
        r"\bRemove-Item\b.*-Recurse.*-Force",
        r"\bRemove-Item\b.*-Force.*-Recurse",
        r"\brmdir\b.*\/s",
        r"\bdel\b.*\/s",
        r"\brd\b.*\/s",
        r"\breg\s+delete\b",
        r"\brm\s+-rf\b",
    ]

    for pattern in patterns:
        if re.search(pattern, command, re.IGNORECASE):
            return (
                "Xavfli buyruq bloklandi. "
                "Bu buyruqni avtomatik bajarish mumkin emas."
            )

    return None


def _execute(
    command: str,
    shell_type: str,
    timeout: int = COMMAND_TIMEOUT,
) -> str:

    if not command.strip():
        return "Xatolik: buyruq bo'sh."

    blocked = _check_dangerous_command(command)

    if blocked:
        return blocked

    timeout = max(1, min(timeout, 120))

    try:
        if shell_type == "cmd":

            if os.name != "nt":
                return (
                    "CMD faqat Windows tizimida ishlaydi. "
                    "Linux'da CMD mavjud emas."
                )

            process_args = [
                "cmd.exe",
                "/d",
                "/s",
                "/c",
                command,
            ]

        elif shell_type == "powershell":

            executable = _get_powershell()

            if not executable:
                return (
                    "PowerShell topilmadi. "
                    "Windows'da powershell, Linux'da pwsh o'rnating."
                )

            process_args = [
                executable,
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                command,
            ]

        else:
            return "Noto'g'ri terminal turi."

        result = subprocess.run(
            process_args,
            cwd=str(CURRENT_DIRECTORY),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            shell=False,
        )

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        output = []

        output.append(f"Terminal: {shell_type.upper()}")
        output.append(f"Working directory: {CURRENT_DIRECTORY}")
        output.append(f"Exit code: {result.returncode}")

        if stdout:
            output.append(f"\nOUTPUT:\n{stdout}")

        if stderr:
            output.append(f"\nERROR:\n{stderr}")

        if not stdout and not stderr:
            output.append("\nBuyruq bajarildi. Natija bo'sh.")

        return _truncate("\n".join(output))

    except subprocess.TimeoutExpired:
        return f"Xatolik: buyruq {timeout} sekund ichida tugamadi."

    except FileNotFoundError as error:
        return f"Terminal topilmadi: {error}"

    except Exception as error:
        return f"Terminal xatosi: {type(error).__name__}: {error}"


# =====================================================
# 1. CMD TOOL
# =====================================================

@tool
def run_cmd(command: str, timeout: int = 60) -> str:
    """
    Windows CMD terminalida buyruq bajaradi.

    Examples:
    - dir
    - python --version
    - pip list
    - pip install fastapi
    - git status
    - docker ps

    CMD faqat Windows tizimida mavjud.
    """
    return _execute(command, "cmd", timeout)


# =====================================================
# 2. POWERSHELL TOOL
# =====================================================

@tool
def run_powershell(command: str, timeout: int = 60) -> str:
    """
    PowerShell terminalida buyruq bajaradi.

    Examples:
    - Get-ChildItem
    - Get-Location
    - Get-Process
    - Get-Service
    - Get-ComputerInfo
    - Get-ChildItem Env:
    - python --version

    Windows PowerShell yoki PowerShell Core talab qilinadi.
    """
    return _execute(command, "powershell", timeout)


# =====================================================
# 3. CURRENT DIRECTORY
# =====================================================

@tool
def get_current_directory() -> str:
    """Hozirgi terminal ishchi papkasini qaytaradi."""

    return (
        f"Current directory: {CURRENT_DIRECTORY}\n"
        f"Workspace root: {WORKSPACE_ROOT}"
    )


# =====================================================
# 4. CHANGE DIRECTORY
# =====================================================

@tool
def set_working_directory(path: str) -> str:
    """
    Terminalning ishchi papkasini o'zgartiradi.

    Faqat workspace ichidagi papkalarga o'tish mumkin.
    """
    global CURRENT_DIRECTORY

    try:
        target = _resolve_path(path)

        if not target.exists():
            return f"Papka topilmadi: {target}"

        if not target.is_dir():
            return f"Bu papka emas: {target}"

        CURRENT_DIRECTORY = target

        return f"Working directory o'zgartirildi:\n{target}"

    except Exception as error:
        return f"Xatolik: {error}"


# =====================================================
# 5. LIST DIRECTORY
# =====================================================

@tool
def list_directory(path: str = ".") -> str:
    """
    Papka ichidagi fayl va papkalarni ko'rsatadi.

    path berilmasa joriy papkani ko'rsatadi.
    """
    try:
        target = _resolve_path(path)

        if not target.exists():
            return f"Papka topilmadi: {target}"

        if not target.is_dir():
            return f"Bu papka emas: {target}"

        items = sorted(
            target.iterdir(),
            key=lambda item: (not item.is_dir(), item.name.lower()),
        )

        lines = [f"Directory: {target}", ""]

        for item in items[:300]:
            kind = "[DIR]" if item.is_dir() else "[FILE]"

            try:
                size = item.stat().st_size
            except OSError:
                size = 0

            lines.append(f"{kind} {item.name} ({size} bytes)")

        if len(items) > 300:
            lines.append("\n[300 ta element ko'rsatildi]")

        return "\n".join(lines)

    except Exception as error:
        return f"Xatolik: {error}"


# =====================================================
# 6. CREATE DIRECTORY
# =====================================================

@tool
def create_directory(path: str) -> str:
    """Workspace ichida yangi papka yaratadi."""

    try:
        target = _resolve_path(path)

        target.mkdir(parents=True, exist_ok=True)

        return f"Papka yaratildi:\n{target}"

    except Exception as error:
        return f"Xatolik: {error}"


# =====================================================
# 7. READ TEXT FILE
# =====================================================

@tool
def read_text_file(path: str) -> str:
    """
    Workspace ichidagi text faylni o'qiydi.

    Python, JSON, TXT, YAML, Markdown kabi
    matnli fayllar uchun ishlatiladi.
    """
    try:
        target = _resolve_path(path)

        if not target.exists():
            return f"Fayl topilmadi: {target}"

        if not target.is_file():
            return "Bu fayl emas."

        if target.stat().st_size > MAX_FILE_SIZE:
            return "Fayl juda katta. Maksimal hajm: 1 MB."

        content = target.read_text(
            encoding="utf-8",
            errors="replace",
        )

        return _truncate(
            f"File: {target}\n\n{content}"
        )

    except Exception as error:
        return f"Xatolik: {error}"


# =====================================================
# 8. WRITE TEXT FILE
# =====================================================

@tool
def write_text_file(
    path: str,
    content: str,
    overwrite: bool = False,
) -> str:
    """
    Workspace ichida text fayl yaratadi yoki yozadi.

    overwrite=False bo'lsa mavjud faylni ustidan yozmaydi.
    overwrite=True bo'lsa mavjud faylni almashtiradi.
    """
    try:
        target = _resolve_path(path)

        if target.exists() and not overwrite:
            return (
                f"Fayl allaqachon mavjud: {target}\n"
                "Ustidan yozish uchun overwrite=True kerak."
            )

        target.parent.mkdir(parents=True, exist_ok=True)

        target.write_text(
            content,
            encoding="utf-8",
        )

        return f"Fayl yozildi:\n{target}"

    except Exception as error:
        return f"Xatolik: {error}"


# =====================================================
# 9. FIND FILES
# =====================================================

@tool
def find_files(
    pattern: str,
    path: str = ".",
) -> str:
    """
    Workspace ichidan fayllarni nomi yoki pattern bo'yicha qidiradi.

    Examples:
    - pattern='*.py'
    - pattern='*.json'
    - pattern='*agent*'
    - pattern='*.txt'
    """
    try:
        target = _resolve_path(path)

        if not target.exists() or not target.is_dir():
            return f"Papka topilmadi: {target}"

        results = list(target.rglob(pattern))

        lines = [
            f"Search pattern: {pattern}",
            f"Search directory: {target}",
            f"Found: {len(results)}",
            "",
        ]

        for item in results[:200]:
            lines.append(str(item))

        if len(results) > 200:
            lines.append("\n[200 ta natija ko'rsatildi]")

        return "\n".join(lines)

    except Exception as error:
        return f"Xatolik: {error}"


# =====================================================
# EXPORT ALL TOOLS
# =====================================================

TERMINAL_TOOLS = [
    run_cmd,
    run_powershell,
    get_current_directory,
    set_working_directory,
    list_directory,
    create_directory,
    read_text_file,
    write_text_file,
    find_files,
]
