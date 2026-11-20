from __future__ import annotations
import ast
import json
import os
import re
import shutil
import subprocess

from datetime import datetime
from importlib import metadata
from pathlib import Path

from langchain_core.tools import tool

# ============================================================
# CONFIGURATION
# ============================================================

WORKSPACE = Path(
    os.getenv("SELF_EXPANDING_WORKSPACE", str(Path.cwd()))
).expanduser().resolve()

IGNORED_DIRS = {
    ".git", ".venv", "venv", "__pycache__",
    "node_modules", ".idea", ".pytest_cache",
    "dist", "build"
}

MAX_FILE_SIZE = 1_000_000
MAX_OUTPUT = 12000
MAX_TIMEOUT = 120

# Python import nomi -> PyPI package nomi
PACKAGE_MAP = {
    "cv2": "opencv-python",
    "PIL": "Pillow",
    "yaml": "PyYAML",
    "dotenv": "python-dotenv",
    "sklearn": "scikit-learn",
    "bs4": "beautifulsoup4",
    "fitz": "PyMuPDF",
    "pydantic_settings": "pydantic-settings",
}


# ============================================================
# COMMON HELPERS
# ============================================================

def resolve_path(path: str) -> Path:
    target = Path(path).expanduser()

    if not target.is_absolute():
        target = WORKSPACE / target

    target = target.resolve()

    try:
        target.relative_to(WORKSPACE)
    except ValueError:
        raise ValueError("Workspace tashqarisiga chiqish mumkin emas.")

    return target


def read_file(path: Path) -> str:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(path)

    if path.stat().st_size > MAX_FILE_SIZE:
        raise ValueError("Fayl hajmi 1 MB dan katta.")

    return path.read_text(encoding="utf-8", errors="replace")


def backup_file(path: Path) -> Path:
    backup_dir = WORKSPACE / ".debug_backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    relative = path.relative_to(WORKSPACE)
    backup_name = str(relative).replace("/", "__").replace("\\", "__")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup = backup_dir / f"{backup_name}.{timestamp}.bak"

    shutil.copy2(path, backup)
    return backup


def validate_python(source: str, filename: str = "<unknown>") -> dict:
    try:
        ast.parse(source, filename=filename)
        return {"valid": True, "error": None}
    except SyntaxError as error:
        return {
            "valid": False,
            "error": {
                "message": error.msg,
                "line": error.lineno,
                "column": error.offset,
                "text": error.text,
            }
        }


def json_result(data) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def run_command(args: list[str], timeout: int = 60) -> dict:
    try:
        result = subprocess.run(
            args,
            cwd=str(WORKSPACE),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=max(1, min(timeout, MAX_TIMEOUT)),
            shell=False,
        )

        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout[-MAX_OUTPUT:],
            "stderr": result.stderr[-MAX_OUTPUT:],
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": f"Timeout: {timeout} sekund."
        }

    except Exception as error:
        return {
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": str(error)
        }


# ============================================================
# 1. ANALYZE ERROR
# ============================================================

@tool
def analyze_error(traceback_text: str) -> str:
    """
    Python traceback'ni tahlil qiladi.

    Xato turi, xabar, fayl, qator va oxirgi traceback
    frame'larini ajratib beradi.
    """

    frames = re.findall(
        r'File "([^"]+)", line (\d+), in ([^\n]+)',
        traceback_text
    )

    error_match = re.search(
        r"^([A-Za-z_][A-Za-z0-9_]*(?:Error|Exception)):\s*(.*)$",
        traceback_text.strip(),
        re.MULTILINE
    )

    return json_result({
        "error_type": error_match.group(1) if error_match else "Unknown",
        "error_message": error_match.group(2) if error_match else "",
        "frames": [
            {
                "file": file,
                "line": int(line),
                "function": function.strip(),
            }
            for file, line, function in frames
        ],
        "last_frame": (
            {
                "file": frames[-1][0],
                "line": int(frames[-1][1]),
                "function": frames[-1][2].strip(),
            }
            if frames else None
        ),
        "hint": (
            "Oxirgi traceback frame odatda xato yuz bergan joyni ko'rsatadi. "
            "Ammo sabab undan oldingi kodda ham bo'lishi mumkin."
        )
    })


# ============================================================
# 2. READ ERROR FILE
# ============================================================

@tool
def read_error_file(path: str, line: int = 0, context: int = 10) -> str:
    """
    Xato chiqqan faylni o'qiydi.

    line=0: butun faylni ko'rsatadi.
    line=25: 25-qator atrofini ko'rsatadi.
    """

    try:
        target = resolve_path(path)
        source = read_file(target)
        lines = source.splitlines()

        if line <= 0:
            start, end = 0, len(lines)
        else:
            context = max(1, min(context, 50))
            start = max(0, line - 1 - context)
            end = min(len(lines), line + context)

        result = []

        for index in range(start, end):
            marker = " >>> " if index == line - 1 else "     "
            result.append(
                f"{marker}{index + 1:4}: {lines[index]}"
            )

        return "\n".join(result)

    except Exception as error:
        return f"Faylni o'qishda xatolik: {error}"


# ============================================================
# 3. SEARCH ERROR IN PROJECT
# ============================================================

@tool
def search_error_in_project(
        query: str,
        file_extension: str = ".py",
        max_results: int = 30,
) -> str:
    """
    Loyiha ichidan matn, funksiya yoki xato nomini qidiradi.
    """

    if not query.strip():
        return "Qidiruv so'rovi bo'sh."

    results = []
    limit = max(1, min(max_results, 100))

    for root, dirs, files in os.walk(WORKSPACE):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]

        for filename in files:
            if file_extension and not filename.endswith(file_extension):
                continue

            path = Path(root) / filename

            try:
                content = read_file(path)
            except Exception:
                continue

            for line_number, line in enumerate(content.splitlines(), 1):
                if query.lower() in line.lower():
                    results.append({
                        "file": str(path.relative_to(WORKSPACE)),
                        "line": line_number,
                        "content": line.strip()[:300],
                    })

                    if len(results) >= limit:
                        return json_result(results)

    return json_result(results)


# ============================================================
# 4. INSPECT FUNCTION
# ============================================================

@tool
def inspect_function(path: str, function_name: str) -> str:
    """
    Python fayl ichidan berilgan funksiyani topadi
    va uning kodini qaytaradi.
    """

    try:
        target = resolve_path(path)
        source = read_file(target)
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(
                    node,
                    (ast.FunctionDef, ast.AsyncFunctionDef)
            ) and node.name == function_name:
                segment = ast.get_source_segment(source, node)

                return segment or "Funksiya kodini ajratib bo'lmadi."

        return f"Funksiya topilmadi: {function_name}"

    except Exception as error:
        return f"Funksiya tahlilida xatolik: {error}"


# ============================================================
# 5. INSPECT CLASS
# ============================================================

@tool
def inspect_class(path: str, class_name: str) -> str:
    """
    Python fayl ichidan berilgan class kodini topadi.
    """

    try:
        target = resolve_path(path)
        source = read_file(target)
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                return (
                        ast.get_source_segment(source, node)
                        or "Class kodini ajratib bo'lmadi."
                )

        return f"Class topilmadi: {class_name}"

    except Exception as error:
        return f"Class tahlilida xatolik: {error}"


# ============================================================
# 6. CHECK IMPORTS
# ============================================================

@tool
def check_imports(path: str) -> str:
    """
    Fayldagi importlarni statik tahlil qiladi.

    Syntax xatosini va loyihadagi mavjud bo'lmagan
    ichki modullarga o'xshash importlarni ko'rsatadi.
    """

    try:
        target = resolve_path(path)
        source = read_file(target)
        tree = ast.parse(source)

        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append({
                        "module": alias.name,
                        "line": node.lineno,
                        "type": "import",
                    })

            elif isinstance(node, ast.ImportFrom):
                imports.append({
                    "module": node.module,
                    "line": node.lineno,
                    "type": "from",
                })

        return json_result({
            "file": str(target.relative_to(WORKSPACE)),
            "syntax": "valid",
            "imports": imports,
            "note": "Bu statik tahlil; importlarni runtime'da ishga tushirmaydi."
        })

    except SyntaxError as error:
        return json_result({
            "syntax": "invalid",
            "line": error.lineno,
            "message": error.msg,
        })

    except Exception as error:
        return f"Import tekshirish xatosi: {error}"


# ============================================================
# 7. CHECK MISSING PACKAGES
# ============================================================

@tool
def check_missing_packages(path: str) -> str:
    """
    Fayldagi tashqi importlarni o'rnatilgan Python
    distribution'lari bilan solishtiradi.
    """

    try:
        target = resolve_path(path)
        tree = ast.parse(read_file(target))

        imports = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split(".")[0])

            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])

        stdlib = getattr(__import__("sys"), "stdlib_module_names", set())
        installed = metadata.packages_distributions()

        missing = []
        available = []

        for module in sorted(imports):
            if module in stdlib or module in {"__future__"}:
                continue

            distributions = installed.get(module, [])

            if distributions:
                available.append({
                    "module": module,
                    "packages": distributions,
                })
                continue

            package_name = PACKAGE_MAP.get(module, module)

            missing.append({
                "module": module,
                "possible_package": package_name,
                "note": "Import nomi va PyPI nomi farq qilishi mumkin."
            })

        return json_result({
            "available": available,
            "possibly_missing": missing,
            "warning": "Bu taxminiy tekshiruv; namespace va editable paketlar noto'g'ri natija berishi mumkin."
        })

    except Exception as error:
        return f"Package tekshirish xatosi: {error}"


# ============================================================
# 8. CHECK CIRCULAR IMPORTS
# ============================================================

@tool
def check_circular_imports() -> str:
    """
    Workspace ichidagi Python modullar import grafigini
    statik tahlil qilib, ehtimoliy circular importlarni topadi.
    """

    module_files = {}

    for root, dirs, files in os.walk(WORKSPACE):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]

        for filename in files:
            if not filename.endswith(".py"):
                continue

            path = Path(root) / filename
            relative = path.relative_to(WORKSPACE).with_suffix("")
            module = ".".join(relative.parts)

            if module.endswith(".__init__"):
                module = module[:-9]

            module_files[module] = path

    graph = {module: set() for module in module_files}

    for module, path in module_files.items():
        try:
            tree = ast.parse(read_file(path))
        except Exception:
            continue

        for node in ast.walk(tree):
            imported = None

            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported = alias.name
                    if imported in graph:
                        graph[module].add(imported)

            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    parts = module.split(".")
                    base = ".".join(parts[:max(0, len(parts) - node.level + 1)])
                    imported = ".".join(
                        part for part in [base, node.module] if part
                    )
                else:
                    imported = node.module or ""

                if imported in graph:
                    graph[module].add(imported)

    cycles = set()

    def visit(start, current, path, active):
        for neighbor in graph.get(current, set()):
            if neighbor == start and len(path) > 1:
                cycle = path[:]
                rotations = [
                    tuple(cycle[i:] + cycle[:i])
                    for i in range(len(cycle))
                ]
                cycles.add(min(rotations))
            elif neighbor not in active and neighbor > start:
                visit(
                    start,
                    neighbor,
                    path + [neighbor],
                    active | {neighbor},
                )

    for module in sorted(graph):
        visit(module, module, [module], {module})

    return json_result({
        "possible_cycles": [list(cycle) for cycle in sorted(cycles)],
        "note": "Statik tekshiruv. Dynamic import va package resolution holatlari to'liq qamrab olinmaydi."
    })


# ============================================================
# 9. FIX SOURCE CODE
# ============================================================

@tool
def fix_source_code(
        path: str,
        old_text: str,
        new_text: str,
) -> str:
    """
    Fayldagi aniq bir kod qismini almashtiradi.

    Xavfsizlik:
    - old_text aynan bir marta uchrashi kerak.
    - Avval backup yaratiladi.
    - Python faylida sintaksis buzilsa, backup tiklanadi.
    """

    try:
        target = resolve_path(path)

        if not target.exists():
            return "Fayl topilmadi."

        if not old_text:
            return "old_text bo'sh bo'lishi mumkin emas."

        original = read_file(target)

        count = original.count(old_text)

        if count != 1:
            return (
                f"Eski kod {count} marta topildi. "
                "Aniqroq old_text yubor."
            )

        updated = original.replace(old_text, new_text, 1)

        if len(updated.encode("utf-8")) > MAX_FILE_SIZE:
            return "Yangi fayl hajmi limitdan katta."

        if target.suffix == ".py":
            validation = validate_python(updated, str(target))

            if not validation["valid"]:
                return json_result({
                    "success": False,
                    "reason": "Yangi kod sintaksis tekshiruvidan o'tmadi.",
                    "syntax_error": validation["error"],
                    "file_changed": False,
                })

        backup = backup_file(target)
        target.write_text(updated, encoding="utf-8")

        return json_result({
            "success": True,
            "file": str(target.relative_to(WORKSPACE)),
            "backup": str(backup.relative_to(WORKSPACE)),
            "message": "Kod yangilandi.",
        })

    except Exception as error:
        return f"Kodni tuzatishda xatolik: {error}"


# ============================================================
# 10. FIX IMPORT ERROR
# ============================================================

@tool
def fix_import_error(
        path: str,
        old_import: str,
        new_import: str,
) -> str:
    """
    Import qatorini aniq almashtiradi.
    """

    if not old_import.strip().startswith(("import ", "from ")):
        return "old_import to'g'ri import qatori bo'lishi kerak."

    if not new_import.strip().startswith(("import ", "from ")):
        return "new_import to'g'ri import qatori bo'lishi kerak."

    return fix_source_code.invoke({
        "path": path,
        "old_text": old_import,
        "new_text": new_import,
    })


# ============================================================
# 11. FIX SYNTAX ERROR
# ============================================================

@tool
def fix_syntax_error(
        path: str,
        old_code: str,
        corrected_code: str,
) -> str:
    """
    Syntax error bo'lgan kod qismini almashtiradi.
    Tuzatilgan fayl ast.parse orqali tekshiriladi.
    """

    return fix_source_code.invoke({
        "path": path,
        "old_text": old_code,
        "new_text": corrected_code,
    })


# ============================================================
# 12. RUN TARGETED TEST
# ============================================================

@tool
def run_targeted_test(
        test_path: str,
        test_name: str = "",
        timeout: int = 60,
) -> str:
    """
    Pytest orqali bitta test fayli yoki test nomini ishga tushiradi.

    Test kodi Python kodini bajaradi. Faqat ishonchli
    kodni izolyatsiyalangan muhitda bajarish kerak.
    """

    try:
        target = resolve_path(test_path)

        if not target.exists():
            return f"Test topilmadi: {test_path}"

        args = [
            "python",
            "-m",
            "pytest",
            str(target),
            "-q",
            "--tb=short",
        ]

        if test_name:
            args.extend(["-k", test_name])

        result = run_command(args, timeout)

        return json_result(result)

    except Exception as error:
        return f"Test bajarishda xatolik: {error}"


# ============================================================
# 13. VERIFY FIX
# ============================================================

@tool
def verify_fix(
        path: str,
        run_tests: bool = False,
        test_path: str = "tests",
) -> str:
    """
    Tuzatilgan faylni tekshiradi.

    1. Fayl mavjudligini tekshiradi.
    2. Python sintaksisini tekshiradi.
    3. Ixtiyoriy pytest testlarini ishga tushiradi.
    """

    try:
        target = resolve_path(path)
        source = read_file(target)

        result = {
            "file": str(target.relative_to(WORKSPACE)),
            "exists": True,
            "syntax": None,
            "tests": None,
        }

        if target.suffix == ".py":
            syntax = validate_python(source, str(target))
            result["syntax"] = syntax

            if not syntax["valid"]:
                result["success"] = False
                return json_result(result)

        if run_tests:
            test_target = resolve_path(test_path)

            if not test_target.exists():
                return f"Test path topilmadi: {test_path}"

            result["tests"] = run_command([
                "python",
                "-m",
                "pytest",
                str(test_target),
                "-q",
                "--tb=short",
            ], timeout=MAX_TIMEOUT)

        result["success"] = (
                result["syntax"] is None
                or result["syntax"]["valid"]
        )

        if run_tests:
            result["success"] = (
                    result["success"] and result["tests"]["success"]
            )

        return json_result(result)

    except Exception as error:
        return f"Verification xatosi: {error}"


# ============================================================
# EXPORT
# ============================================================

DEBUGGING_TOOLS = [
    analyze_error,
    read_error_file,
    search_error_in_project,
    inspect_function,
    inspect_class,
    check_imports,
    check_missing_packages,
    check_circular_imports,
    fix_source_code,
    fix_import_error,
    fix_syntax_error,
    run_targeted_test,
    verify_fix,
]
