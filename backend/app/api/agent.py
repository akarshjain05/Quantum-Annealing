import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user
from app.schemas import AgentAskRequest
from app.agent.orchestrator import answer_question
from app import models

router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.post("/ask")
def ask_agent(req: AgentAskRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    session_id = req.session_id or str(uuid.uuid4())[:12]

    db.add(models.AgentMessage(session_id=session_id, role="user", content=req.question))

    result = answer_question(db, req.question)

    db.add(models.AgentMessage(
        session_id=session_id, role="agent", content=result["answer"],
        tools_used_json=result["tools_used"], sources_json=result["sources"],
    ))
    db.commit()

    return {
        "session_id": session_id,
        "answer": result["answer"],
        "tools_used": result["tools_used"],
        "sources": result["sources"],
        "intent_detected": result["intent"],
        "disclaimer": "Decision-support prototype. No live financial transaction is executed.",
    }


@router.get("/sessions/{session_id}")
def get_session(session_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    msgs = db.query(models.AgentMessage).filter(models.AgentMessage.session_id == session_id).order_by(models.AgentMessage.id).all()
    return [{"role": m.role, "content": m.content, "tools_used": m.tools_used_json, "sources": m.sources_json} for m in msgs]

@router.get("/knowledge")
def get_knowledge(db: Session = Depends(get_db), user=Depends(get_current_user)):
    items = db.query(models.KnowledgeItem).all()
    return [{
        "id": i.id, "source_type": i.source_type, "title": i.title,
        "content": i.content, "is_synthetic": i.is_synthetic,
        "legal_reviewed": i.legal_reviewed
    } for i in items]
