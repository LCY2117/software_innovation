from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    phase: Mapped[str] = mapped_column(String(30), nullable=False, default="CREATED")
    lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    lng: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    roles: Mapped[list["IncidentRole"]] = relationship(
        "IncidentRole", back_populates="incident", cascade="all, delete-orphan"
    )
    logs: Mapped[list["IncidentLog"]] = relationship(
        "IncidentLog", back_populates="incident", cascade="all, delete-orphan",
        order_by="IncidentLog.ts"
    )


class IncidentRole(Base):
    __tablename__ = "incident_roles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    incident_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("incidents.id"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(10), nullable=False)   # PRIME / RUNNER / GUIDE
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="JOINED")
    user_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    incident: Mapped["Incident"] = relationship("Incident", back_populates="roles")


class IncidentLog(Base):
    __tablename__ = "incident_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    incident_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("incidents.id"), nullable=False
    )
    user_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    action: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    msg: Mapped[str] = mapped_column(Text, nullable=False)
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    incident: Mapped["Incident"] = relationship("Incident", back_populates="logs")


class AedLocation(Base):
    __tablename__ = "aed_locations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    floor: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
