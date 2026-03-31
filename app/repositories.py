from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models


async def get_or_create_user(db: AsyncSession, name: str, email: str) -> models.User:
    result = await db.execute(select(models.User).where(models.User.email == email))
    user = result.scalar_one_or_none()
    if user:
        if user.name != name:
            user.name = name
            await db.flush()
        return user
    user = models.User(name=name, email=email)
    db.add(user)
    await db.flush()
    return user


async def get_user_by_email(db: AsyncSession, email: str) -> models.User | None:
    result = await db.execute(select(models.User).where(models.User.email == email))
    return result.scalar_one_or_none()


async def create_session(db: AsyncSession, user_id: str, title: str | None = None) -> models.Session:
    session = models.Session(user_id=user_id, title=title or "New Session")
    db.add(session)
    await db.flush()
    return session


async def get_session(db: AsyncSession, session_id: str) -> models.Session | None:
    return await db.get(models.Session, session_id)


async def create_message(db: AsyncSession, session_id: str, role: str, content: str) -> models.Message:
    message = models.Message(session_id=session_id, role=role, content=content)
    db.add(message)
    await db.flush()
    return message


async def list_messages(db: AsyncSession, session_id: str) -> list[models.Message]:
    stmt = (
        select(models.Message)
        .where(models.Message.session_id == session_id)
        .order_by(models.Message.created_at.asc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_user_sessions(db: AsyncSession, user_id: str) -> list[models.Session]:
    stmt = select(models.Session).where(models.Session.user_id == user_id).order_by(models.Session.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())

