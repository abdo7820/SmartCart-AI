import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from . import config
from .chat import service
from .deps import profile_of, rate_limit, session_user
from .state import state

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(min_length=1, max_length=config.CHAT_MAX_CHARS)
    conversation_id: str | None = Field(default=None, max_length=64)
    context_item_id: int | None = Field(default=None, ge=0)


@router.post("")
def chat(body: ChatIn, acc: dict = Depends(session_user)):
    rate_limit(("chat", acc["id"]), config.CHAT_MAX_PER_MINUTE, 60, "You are sending messages too quickly")
    if not body.message.strip():
        raise HTTPException(422, detail=[{"loc": ["body", "message"], "msg": "Message must not be empty", "type": "value_error"}])
    res = service.handle_chat(state["chat"], acc, profile_of(acc), body.message.strip(), body.conversation_id, body.context_item_id)
    if res is None:
        raise HTTPException(404, "conversation not found")
    return res


@router.get("/conversations")
def conversations(acc: dict = Depends(session_user)):
    return state["adb"].query("SELECT id, title, created_at, updated_at FROM chat_conversations WHERE account_id = ? ORDER BY updated_at DESC LIMIT 50", (acc["id"],))


@router.get("/conversations/{conversation_id}")
def conversation(conversation_id: str, acc: dict = Depends(session_user)):
    conv = service.get_conversation(state["adb"], acc["id"], conversation_id)
    if conv is None:
        raise HTTPException(404, "conversation not found")
    rows = state["adb"].query("SELECT role, content, product_ids, created_at FROM chat_messages WHERE conversation_id = ? ORDER BY created_at, id", (conversation_id,))
    from . import catalog
    ids = sorted({i for r in rows for i in json.loads(r["product_ids"])})
    info = catalog.get_products(state["con"], ids)
    return {"id": conv["id"], "title": conv["title"], "messages": [
        {"role": r["role"], "content": r["content"], "created_at": r["created_at"], "products": [info[i] for i in json.loads(r["product_ids"]) if i in info]} for r in rows]}


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: str, acc: dict = Depends(session_user)):
    adb = state["adb"]
    if service.get_conversation(adb, acc["id"], conversation_id) is None:
        raise HTTPException(404, "conversation not found")
    with adb.transaction():
        adb.execute("DELETE FROM chat_messages WHERE conversation_id = ?", (conversation_id,))
        adb.execute("DELETE FROM chat_conversations WHERE id = ?", (conversation_id,))


@router.delete("/conversations", status_code=204)
def delete_all(acc: dict = Depends(session_user)):
    adb = state["adb"]
    with adb.transaction():
        adb.execute("DELETE FROM chat_messages WHERE conversation_id IN (SELECT id FROM chat_conversations WHERE account_id = ?)", (acc["id"],))
        adb.execute("DELETE FROM chat_conversations WHERE account_id = ?", (acc["id"],))
