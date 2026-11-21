"""Chat endpoint'i — supervisor multi-agent grafini ishga tushiradi."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.deps import get_current_user
from backend.api.models import User
from backend.api.schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post(
    "",
    response_model=ChatResponse,
    summary="AI agentlar bilan suhbat",
    description=(
        "Foydalanuvchi so'rovini supervisor agentga yuboradi. Supervisor so'rovni "
        "tahlil qilib, mos mutaxassis agentni (brauzer, database, document, game, "
        "lesson, rag, research) tanlaydi va yakuniy javobni qaytaradi."
    ),
)
async def chat(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    # Og'ir agentlar/LLM modullari startup'ni sekinlashtirmasligi uchun lazy import.
    from backend.graph.nodes import chat_techflow_ai

    session_id = payload.session_id or f"{current_user.id}-{uuid.uuid4()}"
    try:
        result = await chat_techflow_ai(request=payload.message, session_id=session_id)
    except Exception as exc:  # noqa: BLE001 - xatoni API javobiga aylantiramiz
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Agent ishlashida xatolik: {exc}",
        ) from exc

    serializable_raw = {
        key: value
        for key, value in result.items()
        if value is None or isinstance(value, (str, int, float, bool))
    }

    return ChatResponse(
        session_id=session_id,
        response=result.get("finally_response") or "",
        approved=bool(result.get("response_agent_approved")),
        attempts=int(result.get("attempts") or 0),
        next_agent=result.get("next_agent") or None,
        raw=serializable_raw,
    )
