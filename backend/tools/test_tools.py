from __future__ import annotations

import ast
import json
import os
import shutil
import subprocess
import uuid

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from langchain_core.tools import tool

# ============================================================
# CONFIGURATION
# ============================================================

WORKSPACE = Path(
    os.getenv(
        "SELF_EXPANDING_WORKSPACE",
        str(Path.cwd())
    )
).expanduser().resolve()

AGENTS_DIR = WORKSPACE / "backend" / "agents"
TOOLS_DIR = WORKSPACE / "backend" / "tools"
REGISTRY_DIR = WORKSPACE / "backend" / "registry"

AGENT_REGISTRY_FILE = REGISTRY_DIR / "agents.json"
ROUTING_FILE = REGISTRY_DIR / "supervisor_routes.json"

IGNORED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    ".idea",
    ".pytest_cache",
    "dist",
    "build",
}

MAX_FILE_SIZE = 1_000_000
MAX_TEST_TIMEOUT = 180


# ============================================================
# COMMON HELPERS
# ============================================================

def resolve_path(path: str) -> Path:
    """
    Resolve path and prevent access outside workspace.
    """

    target = Path(path).expanduser()

    if not target.is_absolute():
        target = WORKSPACE / target

    target = target.resolve()

    try:
        target.relative_to(WORKSPACE)
    except ValueError:
        raise ValueError(
            f"Workspace tashqarisiga chiqish mumkin emas: {target}"
        )

    return target


def ensure_parent(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)


def read_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(path)

    if not path.is_file():
        raise ValueError("Bu fayl emas.")

    if path.stat().st_size > MAX_FILE_SIZE:
        raise ValueError("Fayl hajmi 1 MB dan katta.")

    return path.read_text(
        encoding="utf-8",
        errors="replace"
    )


def write_text(path: Path, content: str):
    ensure_parent(path)

    path.write_text(
        content,
        encoding="utf-8"
    )


def run_process(
        args: list[str],
        timeout: int = 60
) -> dict:
    """
    Run subprocess without shell=True.
    """

    try:
        result = subprocess.run(
            args,
            cwd=str(WORKSPACE),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            shell=False,
        )

        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout[-12000:],
            "stderr": result.stderr[-12000:],
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


def load_json(path: Path, default):
    if not path.exists():
        return default

    try:
        return json.loads(read_text(path))
    except json.JSONDecodeError:
        raise ValueError(f"JSON fayl noto'g'ri: {path}")


def save_json(path: Path, data):
    write_text(
        path,
        json.dumps(
            data,
            indent=4,
            ensure_ascii=False
        )
    )


def valid_python_name(name: str) -> bool:
    return (
            name.isidentifier()
            and not name.startswith("__")
    )


# ============================================================
# 1. INSPECT PROJECT
# ============================================================

@tool
def inspect_project(max_items: int = 300) -> str:
    """
    Loyihaning papka va fayl strukturasini o'rganadi.

    Coding Agent loyiha bilan ishlashni boshlashdan
    oldin ushbu tool'dan foydalanishi mumkin.
    """

    if not WORKSPACE.exists():
        return f"Workspace topilmadi: {WORKSPACE}"

    lines = [
        f"PROJECT: {WORKSPACE}",
        ""
    ]

    count = 0

    for root, dirs, files in os.walk(WORKSPACE):
        dirs[:] = [
            d for d in dirs
            if d not in IGNORED_DIRS
        ]

        current = Path(root)

        relative = current.relative_to(WORKSPACE)

        depth = len(relative.parts)

        indent = "    " * depth

        lines.append(f"{indent}[DIR] {current.name}")

        for filename in sorted(files):
            lines.append(
                f"{indent}    [FILE] {filename}"
            )

            count += 1

            if count >= max(1, min(max_items, 1000)):
                lines.append("... LIMIT REACHED ...")
                return "\n".join(lines)

    return "\n".join(lines)


# ============================================================
# 2. LIST AGENTS
# ============================================================

@tool
def list_agents() -> str:
    """
    backend/agents ichidagi Python agent fayllarini topadi.
    """

    if not AGENTS_DIR.exists():
        return f"Agents directory topilmadi: {AGENTS_DIR}"

    agents = []

    for file in sorted(AGENTS_DIR.glob("*.py")):
        if file.name == "__init__.py":
            continue

        agents.append({
            "name": file.stem,
            "file": str(file.relative_to(WORKSPACE)),
            "size": file.stat().st_size,
        })

    return json.dumps(
        agents,
        ensure_ascii=False,
        indent=4
    )


# ============================================================
# 3. INSPECT AGENT
# ============================================================

@tool
def inspect_agent(agent_name: str) -> str:
    """
    Berilgan agentning Python kodini o'qiydi.

    Masalan:
    inspect_agent("research_agent")
    """

    if not valid_python_name(agent_name):
        return "Noto'g'ri agent nomi."

    path = resolve_path(
        str(Path("backend") / "agents" / f"{agent_name}.py")
    )

    try:
        return read_text(path)
    except Exception as error:
        return f"Xatolik: {error}"


# ============================================================
# 4. INSPECT GRAPH
# ============================================================

@tool
def inspect_graph(path: str) -> str:
    """
    LangGraph kodidagi node, edge va conditional
    edge'larni AST yordamida aniqlaydi.

    Bu kodni ishga tushirmaydi.
    """

    try:
        target = resolve_path(path)
        source = read_text(target)

        tree = ast.parse(source)

        result = {
            "file": str(target),
            "nodes": [],
            "edges": [],
            "conditional_edges": [],
            "functions": [],
            "classes": [],
        }

        for node in ast.walk(tree):

            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                result["functions"].append(node.name)

            elif isinstance(node, ast.ClassDef):
                result["classes"].append(node.name)

            elif isinstance(node, ast.Call):

                func = node.func

                if isinstance(func, ast.Attribute):
                    method = func.attr

                    if method == "add_node":
                        result["nodes"].append(
                            ast.unparse(node.args)
                        )

                    elif method == "add_edge":
                        result["edges"].append(
                            ast.unparse(node.args)
                        )

                    elif method == "add_conditional_edges":
                        result["conditional_edges"].append(
                            ast.unparse(node.args)
                        )

        return json.dumps(
            result,
            ensure_ascii=False,
            indent=4
        )

    except Exception as error:
        return f"Graph tahlilida xatolik: {error}"


# ============================================================
# 5. CREATE AGENT
# ============================================================

@tool
def create_agent(
        agent_name: str,
        description: str,
        system_prompt: str,
        tools_variable: str = "AGENT_TOOLS",
) -> str:
    """
    Yangi LangChain agent uchun Python fayl yaratadi.

    Fayl backend/agents ichida yaratiladi.

    Tool yaratish va test qilish alohida bajariladi.
    """

    if not valid_python_name(agent_name):
        return "Agent nomi Python identifier bo'lishi kerak."

    if not valid_python_name(tools_variable):
        return "tools_variable noto'g'ri."

    path = resolve_path(
        str(Path("backend") / "agents" / f"{agent_name}.py")
    )

    if path.exists():
        return f"Agent allaqachon mavjud: {path}"

    template = f'''"""
{description}
"""

from langchain.agents import create_agent

from backend.tools.{agent_name}_tools import {tools_variable}


SYSTEM_PROMPT = {system_prompt!r}


def build_{agent_name}(model):
    """
    Yangi agentni yaratadi.
    """

    return create_agent(
        model=model,
        tools={tools_variable},
        system_prompt=SYSTEM_PROMPT,
    )
'''

    try:
        write_text(path, template)

        return (
            f"Agent fayli yaratildi: "
            f"{path.relative_to(WORKSPACE)}\n"
            "Eslatma: agent ishga tushishi uchun uning tool "
            "moduli va model konfiguratsiyasi ham tayyor bo'lishi kerak."
        )

    except Exception as error:
        return f"Agent yaratishda xatolik: {error}"


# ============================================================
# 6. CREATE TOOL
# ============================================================

@tool
def create_tool(
        tool_name: str,
        description: str,
        function_code: str,
) -> str:
    """
    Yangi LangChain tool funksiyasini Python moduliga yozadi.

    function_code ichida @tool bilan belgilangan
    Python funksiyasi bo'lishi kerak.

    Bu kod avtomatik ishga tushirilmaydi.
    """

    if not valid_python_name(tool_name):
        return "Tool nomi noto'g'ri."

    try:
        tree = ast.parse(function_code)

        functions = [
            node for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]

        if not functions:
            return "function_code ichida funksiya topilmadi."

        if not any(
                isinstance(node, ast.ImportFrom)
                and node.module == "langchain_core.tools"
                and any(alias.name == "tool" for alias in node.names)
                for node in tree.body
        ):
            return "Kodda from langchain_core.tools import tool bo'lishi kerak."

        target = resolve_path(
            str(Path("backend") / "tools" / f"{tool_name}_tools.py")
        )

        if target.exists():
            return f"Tool moduli allaqachon mavjud: {target}"

        module_code = (
                '"""Generated LangChain tools."""\n\n'
                "from langchain_core.tools import tool\n\n\n"
                f"# {description}\n\n"
                f"{function_code.strip()}\n\n"
                f"{tool_name.upper()}_TOOLS = [\n"
                + "".join(
            f"    {fn.name},\n"
            for fn in functions
        )
                + "]\n"
        )

        write_text(target, module_code)

        return (
            f"Tool moduli yaratildi: "
            f"{target.relative_to(WORKSPACE)}\n"
            "Keyingi qadam: sintaksisni tekshirish va test yozish."
        )

    except SyntaxError as error:
        return (
            f"Python syntax error: {error.msg}, "
            f"line: {error.lineno}"
        )

    except Exception as error:
        return f"Tool yaratishda xatolik: {error}"


# ============================================================
# 7. CREATE SOURCE FILE
# ============================================================

@tool
def create_source_file(
        path: str,
        content: str,
        overwrite: bool = False,
) -> str:
    """
    Workspace ichida yangi source fayl yaratadi.

    overwrite=False bo'lsa mavjud faylni almashtirmaydi.
    """

    try:
        target = resolve_path(path)

        if target.exists() and not overwrite:
            return "Fayl mavjud. overwrite=True berish kerak."

        if len(content.encode("utf-8")) > MAX_FILE_SIZE:
            return "Fayl hajmi 1 MB dan katta."

        if target.suffix == ".py":
            ast.parse(content)

        write_text(target, content)

        return (
            f"Fayl yaratildi: "
            f"{target.relative_to(WORKSPACE)}"
        )

    except SyntaxError as error:
        return (
            f"Python syntax error: {error.msg}, "
            f"line: {error.lineno}"
        )

    except Exception as error:
        return f"Fayl yaratishda xatolik: {error}"


# ============================================================
# 8. MODIFY SOURCE FILE
# ============================================================

@tool
def modify_source_file(
        path: str,
        old_text: str,
        new_text: str,
) -> str:
    """
    Fayl ichidagi aniq kod qismini almashtiradi.

    old_text faylda aynan bir marta uchrashi shart.
    Bu tasodifiy ko'p joyni o'zgartirishning oldini oladi.
    """

    try:
        target = resolve_path(path)

        content = read_text(target)

        if not old_text:
            return "old_text bo'sh bo'lishi mumkin emas."

        count = content.count(old_text)

        if count == 0:
            return "O'zgartiriladigan kod topilmadi."

        if count > 1:
            return (
                f"Kod {count} ta joyda topildi. "
                "Aniqroq old_text yubor."
            )

        updated = content.replace(
            old_text,
            new_text,
            1
        )

        if target.suffix == ".py":
            ast.parse(updated)

        write_text(target, updated)

        return (
            f"Fayl yangilandi: "
            f"{target.relative_to(WORKSPACE)}"
        )

    except SyntaxError as error:
        return (
            f"O'zgarish sintaksis xatosini keltirib chiqardi: "
            f"{error.msg}, line {error.lineno}"
        )

    except Exception as error:
        return f"Faylni o'zgartirishda xatolik: {error}"


# ============================================================
# 9. VALIDATE PYTHON SYNTAX
# ============================================================

@tool
def validate_python_syntax(path: str) -> str:
    """
    Python fayl sintaksisini tekshiradi.
    Faylni ishga tushirmaydi.
    """

    try:
        target = resolve_path(path)

        source = read_text(target)

        ast.parse(
            source,
            filename=str(target)
        )

        return (
            f"SUCCESS: Python syntax to'g'ri.\n"
            f"File: {target.relative_to(WORKSPACE)}"
        )

    except SyntaxError as error:
        return (
            "SYNTAX ERROR\n"
            f"File: {path}\n"
            f"Line: {error.lineno}\n"
            f"Column: {error.offset}\n"
            f"Message: {error.msg}"
        )

    except Exception as error:
        return f"Validation xatosi: {error}"


# ============================================================
# 10. RUN UNIT TESTS
# ============================================================

@tool
def run_unit_tests(
        test_path: str = "tests",
        timeout: int = 120,
) -> str:
    """
    Workspace ichida pytest testlarini bajaradi.

    Faqat ishonchli test kodlarini izolyatsiyalangan
    muhitda ishga tushirish kerak.
    """

    try:
        target = resolve_path(test_path)

        if not target.exists():
            return f"Test path topilmadi: {target}"

        timeout = max(1, min(timeout, MAX_TEST_TIMEOUT))

        result = run_process(
            [
                "python",
                "-m",
                "pytest",
                str(target),
                "-q",
                "--tb=short",
            ],
            timeout=timeout,
        )

        return json.dumps(
            result,
            ensure_ascii=False,
            indent=4
        )

    except Exception as error:
        return f"Test xatosi: {error}"


# ============================================================
# 11. CREATE FEATURE BRANCH
# ============================================================

@tool
def create_feature_branch(branch_name: str) -> str:
    """
    Git repository ichida yangi feature branch yaratadi.

    Branch nomi oddiy harf, raqam, '-' va '_' dan iborat bo'lishi kerak.
    """

    if not branch_name or len(branch_name) > 80:
        return "Branch nomi noto'g'ri."

    if not all(
            char.isalnum() or char in "-_/"
            for char in branch_name
    ):
        return "Branch nomida ruxsat etilmagan belgi bor."

    result = run_process(
        [
            "git",
            "switch",
            "-c",
            branch_name
        ],
        timeout=30,
    )

    return json.dumps(
        result,
        ensure_ascii=False,
        indent=4
    )


# ============================================================
# 12. GIT DIFF
# ============================================================

@tool
def git_diff(staged: bool = False) -> str:
    """
    Git o'zgarishlarini ko'rsatadi.

    staged=False: working tree farqlari.
    staged=True: indexga qo'shilgan farqlar.
    """

    args = ["git", "diff"]

    if staged:
        args.append("--cached")

    result = run_process(
        args,
        timeout=30
    )

    return json.dumps(
        result,
        ensure_ascii=False,
        indent=4
    )


# ============================================================
# 13. REGISTER AGENT
# ============================================================

@tool
def register_agent(
        agent_name: str,
        description: str,
        capabilities: list[str],
        tools: list[str],
) -> str:
    """
    Agentni backend/registry/agents.json fayliga ro'yxatdan o'tkazadi.

    Agent kodi avval yaratilgan bo'lishi kerak.
    """

    if not valid_python_name(agent_name):
        return "Agent nomi noto'g'ri."

    agent_file = resolve_path(
        str(Path("backend") / "agents" / f"{agent_name}.py")
    )

    if not agent_file.exists():
        return "Agent Python fayli topilmadi."

    try:
        REGISTRY_DIR.mkdir(parents=True, exist_ok=True)

        registry = load_json(
            AGENT_REGISTRY_FILE,
            {}
        )

        if agent_name in registry:
            return "Agent allaqachon registry'da mavjud."

        registry[agent_name] = {
            "name": agent_name,
            "description": description,
            "capabilities": capabilities,
            "tools": tools,
            "module": f"backend.agents.{agent_name}",
            "status": "pending_review",
            "created_at": datetime.now(
                timezone.utc
            ).isoformat(),
        }

        save_json(
            AGENT_REGISTRY_FILE,
            registry
        )

        return (
            f"Agent registry'ga qo'shildi: {agent_name}\n"
            "Status: pending_review\n"
            "Eslatma: mustaqil review va integration testdan "
            "keyin active holatga o'tkaz."
        )

    except Exception as error:
        return f"Registry xatosi: {error}"


# ============================================================
# 14. UPDATE SUPERVISOR ROUTING
# ============================================================

@tool
def update_supervisor_routing(
        capability: str,
        agent_name: str,
        description: str,
) -> str:
    """
    Supervisor routing registry'ga yangi capability qo'shadi.

    Bu JSON registry'ni yangilaydi.
    Supervisor koding avtomatik o'zgarmaydi:
    u runtime'da ushbu registry'ni o'qishi kerak.
    """

    if not valid_python_name(agent_name):
        return "Agent nomi noto'g'ri."

    if not valid_python_name(capability):
        return "Capability nomi noto'g'ri."

    try:
        agents = load_json(
            AGENT_REGISTRY_FILE,
            {}
        )

        if agent_name not in agents:
            return "Agent avval register_agent orqali qo'shilishi kerak."

        if agents[agent_name].get("status") != "active":
            return (
                "Agent active emas. "
                "Avval review va testdan o'tkazish kerak."
            )

        REGISTRY_DIR.mkdir(parents=True, exist_ok=True)

        routes = load_json(
            ROUTING_FILE,
            {}
        )

        if capability in routes:
            return "Bu capability routing'da allaqachon mavjud."

        routes[capability] = {
            "agent": agent_name,
            "description": description,
            "status": "active",
        }

        save_json(
            ROUTING_FILE,
            routes
        )

        return (
            f"Supervisor routing yangilandi.\n"
            f"Capability: {capability}\n"
            f"Agent: {agent_name}"
        )

    except Exception as error:
        return f"Routing xatosi: {error}"


# ============================================================
# 15. ROLLBACK CHANGES
# ============================================================

@tool
def rollback_changes(
        path: str,
        approved: bool = False,
) -> str:
    """
    Bitta faylni Git HEAD holatiga qaytaradi.

    Bu amal fayldagi commit qilinmagan o'zgarishlarni yo'qotadi.
    Faqat approved=True bo'lganda bajariladi.

    Git'da kuzatiladigan fayllar uchungina ishlaydi.
    """

    if not approved:
        return (
            "Rollback bajarilmadi. "
            "Foydalanuvchi tasdig'i kerak: approved=True."
        )

    try:
        target = resolve_path(path)

        relative = target.relative_to(WORKSPACE)

        if not target.exists():
            return "Fayl mavjud emas."

        result = run_process(
            [
                "git",
                "restore",
                "--worktree",
                "--",
                str(relative),
            ],
            timeout=30,
        )

        if result["success"]:
            return (
                f"Fayl Git HEAD holatiga qaytarildi:\n"
                f"{relative}"
            )

        return json.dumps(
            result,
            ensure_ascii=False,
            indent=4
        )

    except Exception as error:
        return f"Rollback xatosi: {error}"


# ============================================================
# EXPORT
# ============================================================

TEST_SELF_EXPANDING_TOOLS = [
    inspect_project,
    list_agents,
    inspect_agent,
    inspect_graph,
    create_agent,
    create_tool,
    create_source_file,
    modify_source_file,
    validate_python_syntax,
    run_unit_tests,
    create_feature_branch,
    git_diff,
    register_agent,
    update_supervisor_routing,
    rollback_changes,
]
