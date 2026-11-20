
from __future__ import annotations

from langchain_core.tools import tool
from langchain_community.agent_toolkits.file_management import (
    FileManagementToolkit,
)
from langchain_community.document_loaders import (
    UnstructuredWordDocumentLoader,
    UnstructuredExcelLoader,
    PyPDFLoader,
    TextLoader,
    CSVLoader,
    YoutubeLoader,
    UnstructuredURLLoader,
    UnstructuredPDFLoader,
    JSONLoader,
)


# =========================================================
# 1. WORD FILE
# =========================================================

@tool
def read_word_file(file_path: str) -> dict:
    """Word hujjatini o'qish va matni hamda metadata ma'lumotlarini olish."""
    loader = UnstructuredWordDocumentLoader(file_path)
    documents = loader.load()

    return {
        "document": [doc.page_content for doc in documents],
        "metadata": [doc.metadata for doc in documents],
        "file_path": file_path,
    }


# =========================================================
# 2. EXCEL FILE
# =========================================================

@tool
def read_excel_file(file_path: str) -> dict:
    """Excel faylini o'qish va uning matni hamda metadata ma'lumotlarini olish."""
    loader = UnstructuredExcelLoader(file_path)
    documents = loader.load()

    return {
        "document": [doc.page_content for doc in documents],
        "metadata": [doc.metadata for doc in documents],
        "file_path": file_path,
    }


# =========================================================
# 3. PDF FILE
# =========================================================

@tool
def read_pdf_file(file_path: str) -> dict:
    """PDF hujjatini o'qish va matni hamda metadata ma'lumotlarini olish."""
    loader = UnstructuredPDFLoader(file_path)
    documents = loader.load()

    return {
        "document": [doc.page_content for doc in documents],
        "metadata": [doc.metadata for doc in documents],
        "file_path": file_path,
    }


# =========================================================
# 4. TEXT FILE
# =========================================================

@tool
def read_text_file(file_path: str) -> dict:
    """TXT faylini o'qish va uning matni hamda metadata ma'lumotlarini olish."""
    loader = TextLoader(file_path, encoding="utf-8")
    documents = loader.load()

    return {
        "document": [doc.page_content for doc in documents],
        "metadata": [doc.metadata for doc in documents],
        "file_path": file_path,
    }


# =========================================================
# 5. JSON FILE
# =========================================================

@tool
def read_json_file(file_path: str) -> dict:
    """JSON faylini o'qish va tarkibi hamda metadata ma'lumotlarini olish."""
    loader = JSONLoader(
        file_path=file_path,
        jq_schema=".",
        text_content=False,
    )
    documents = loader.load()

    return {
        "document": [doc.page_content for doc in documents],
        "metadata": [doc.metadata for doc in documents],
        "file_path": file_path,
    }


# =========================================================
# 6. FILE MANAGEMENT TOOLKIT
# =========================================================

file_toolkit = FileManagementToolkit(
    root_dir="../creating_files"
)

file_management_tools = file_toolkit.get_tools()


# =========================================================
# 7. ALL FILE TOOLS
# =========================================================

FILE_MANAGMENT_TOOLS = (
    file_management_tools
    + [
        read_word_file,
        read_excel_file,
        read_pdf_file,
        read_text_file,
        read_json_file,
    ]
)
