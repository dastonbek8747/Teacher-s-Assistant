"""Tizimdagi mutaxassis agentlar ro'yxati va tavsifi."""
from backend.api.schemas import AgentInfo

AGENTS: list[AgentInfo] = [
    AgentInfo(
        key="brauzer",
        node="brauzer_node",
        description="Brauzerni to'liq boshqaradi: e-maktab, YouTube, Telegram web va boshqa "
        "saytlarga kiradi, bosadi, yozadi, ma'lumot o'qiydi. Jonli (real vaqt) ma'lumot uchun.",
    ),
    AgentInfo(
        key="database",
        node="db_node",
        description="Baza bilan ishlaydi: jadval yaratish, yozish, o'qish, yangilash, o'chirish. "
        "Foydalanuvchining shaxsiy, tuzilgan eslatmalari uchun.",
    ),
    AgentInfo(
        key="document",
        node="document_node",
        description="PDF, Word, Excel, PPTX fayllarni o'qiydi, yozadi va yaratadi.",
    ),
    AgentInfo(
        key="game",
        node="game_node",
        description="Mavzu bo'yicha ishlaydigan bitta .html o'yin yaratadi.",
    ),
    AgentInfo(
        key="lesson",
        node="lesson_node",
        description="Mavzu va sinf uchun yangicha dars metodlari, dars rejasi va faollik g'oyalari.",
    ),
    AgentInfo(
        key="rag",
        node="rag_node",
        description="Fayllarni vektor ko'rinishida (Qdrant) saqlaydi va ma'no bo'yicha qidiradi.",
    ),
    AgentInfo(
        key="research",
        node="research_node",
        description="Internetdan chuqur, manbali qidiruv olib boradi.",
    ),
]
