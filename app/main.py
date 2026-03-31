from __future__ import annotations

import json

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent import AssistantAgent
from app.config import settings
from app.db import Base, engine, get_db
from app import repositories, schemas

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = AssistantAgent()


@app.on_event("startup")
async def on_startup() -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                DO $$
                BEGIN
                    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'message_role') THEN
                        IF NOT EXISTS (
                            SELECT 1
                            FROM pg_type t
                            JOIN pg_enum e ON t.oid = e.enumtypid
                            WHERE t.typname = 'message_role' AND e.enumlabel = 'tool'
                        ) THEN
                            ALTER TYPE message_role ADD VALUE 'tool';
                        END IF;
                    END IF;
                END $$;
                """
            )
        )
        await conn.run_sync(Base.metadata.create_all)


@app.get("/")
async def root() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


@app.post("/api/users", response_model=schemas.UserRead)
async def create_user(payload: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    user = await repositories.get_or_create_user(db, name=payload.name, email=payload.email)
    await db.commit()
    await db.refresh(user)
    return user


@app.post("/api/sessions", response_model=schemas.SessionRead)
async def create_session(payload: schemas.SessionCreate, db: AsyncSession = Depends(get_db)):
    session = await repositories.create_session(db, user_id=payload.user_id, title=payload.title)
    await db.commit()
    await db.refresh(session)
    return session


@app.get("/api/users/sessions", response_model=list[schemas.SessionRead])
async def get_user_sessions(email: str = Query(...), db: AsyncSession = Depends(get_db)):
    user = await repositories.get_user_by_email(db, email=email)
    if not user:
        return []
    return await repositories.list_user_sessions(db, user_id=user.id)


@app.get("/api/sessions/{session_id}/messages", response_model=list[schemas.MessageRead])
async def get_session_messages(session_id: str, db: AsyncSession = Depends(get_db)):
    session = await repositories.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return await repositories.list_messages(db, session_id=session_id)


@app.post("/api/chat", response_model=schemas.ChatResponse)
async def chat(payload: schemas.ChatRequest, db: AsyncSession = Depends(get_db)):
    user = await repositories.get_or_create_user(db, name=payload.user_name, email=payload.user_email)

    session = await repositories.get_session(db, payload.session_id) if payload.session_id else None
    if not session:
        title = payload.message[:80] if payload.message else "New Session"
        session = await repositories.create_session(db, user_id=user.id, title=title)

    history = [
        {"role": msg.role, "content": msg.content}
        for msg in await repositories.list_messages(db, session_id=session.id)
        if msg.role in ("user", "assistant")
    ]

    await repositories.create_message(db, session_id=session.id, role="user", content=payload.message)

    answer, trace = await agent.run(payload.message, history)
    await repositories.create_message(db, session_id=session.id, role="assistant", content=answer)
    for event in trace:
        await repositories.create_message(
            db,
            session_id=session.id,
            role="tool",
            content=json.dumps(event, ensure_ascii=False),
        )

    await db.commit()
    return schemas.ChatResponse(session_id=session.id, answer=answer, tool_trace=trace)

