import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Supervisor(Base):
    __tablename__ = "supervisors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    base_instruction: Mapped[str] = mapped_column(Text, nullable=False)
    available_actions: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="[]")
    wake_up_behavior: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    wake_aggressiveness: Mapped[str] = mapped_column(String(50), nullable=False, server_default="normal")
    llm_settings: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
