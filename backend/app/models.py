from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base
def now(): return datetime.now(timezone.utc)
class Appointment(Base):
    __tablename__ = "appointments"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    customer_name: Mapped[str] = mapped_column(String(120)); customer_reference: Mapped[str] = mapped_column(String(80)); service_type: Mapped[str] = mapped_column(String(80))
    appointment_date: Mapped[str] = mapped_column(String(10)); appointment_time: Mapped[str] = mapped_column(String(5)); status: Mapped[str] = mapped_column(String(20), default="BOOKED"); version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now); updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
class Operation(Base):
    __tablename__ = "operations"
    operation_id: Mapped[str] = mapped_column(String(40), primary_key=True); idempotency_key: Mapped[str] = mapped_column(String(160), unique=True, index=True); operation_type: Mapped[str] = mapped_column(String(40)); appointment_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    request_fingerprint: Mapped[str] = mapped_column(String(64)); requested_payload: Mapped[str] = mapped_column(Text); status: Mapped[str] = mapped_column(String(20)); result_payload: Mapped[str | None] = mapped_column(Text, nullable=True); error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now); updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now); committed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
class Event(Base):
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True); timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now); operation_id: Mapped[str | None] = mapped_column(String(40), nullable=True); appointment_id: Mapped[str | None] = mapped_column(String(40), nullable=True); event_type: Mapped[str] = mapped_column(String(60)); severity: Mapped[str] = mapped_column(String(20), default="INFO"); message: Mapped[str] = mapped_column(String(240)); metadata_json: Mapped[str] = mapped_column(Text, default="{}")
class Escalation(Base):
    __tablename__ = "escalations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True); operation_id: Mapped[str] = mapped_column(String(40)); reason: Mapped[str] = mapped_column(String(240)); status: Mapped[str] = mapped_column(String(20), default="OPEN"); created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
