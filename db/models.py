import enum
import uuid
from sqlalchemy import (
    Column, Integer, Boolean, Numeric, Text, ForeignKey, DateTime,
    UniqueConstraint, Enum
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()


class Site(Base):
    __tablename__ = 'sites'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    display_name = Column(Text, nullable=False)
    tz = Column(Text, nullable=False, default='UTC')
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    devices = relationship("Device", back_populates="site", cascade="all, delete")
    points = relationship("Point", back_populates="site", cascade="all, delete")


class Device(Base):
    __tablename__ = 'devices'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id = Column(UUID(as_uuid=True), ForeignKey('sites.id', ondelete='CASCADE'), nullable=False)
    model = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    site = relationship("Site", back_populates="devices")
    state = relationship("DeviceState", uselist=False, back_populates="device", cascade="all, delete")


class Point(Base):
    __tablename__ = 'points'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)  # UUID PK
    site_id = Column(UUID(as_uuid=True), ForeignKey('sites.id', ondelete='CASCADE'), nullable=False)
    point_name = Column(Text, nullable=False)
    unit = Column(Text, nullable=False)
    tags = Column(JSONB, nullable=False, default=dict)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (UniqueConstraint('site_id', 'point_name', name='uq_points_site_name'),)

    site = relationship("Site", back_populates="points")
    metadata_history = relationship("PointMetadataHistory", back_populates="point", cascade="all, delete")
    validation_rules = relationship("ValidationRule", back_populates="point", cascade="all, delete")


class PointMetadataHistory(Base):
    __tablename__ = 'point_metadata_history'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    point_id = Column(UUID(as_uuid=True), ForeignKey('points.id', ondelete='CASCADE'), nullable=False)
    effective_from = Column(DateTime(timezone=True), nullable=False)
    unit = Column(Text, nullable=False)
    tags = Column(JSONB, nullable=False)
    meta_hash = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    point = relationship("Point", back_populates="metadata_history")


class Measurement(Base):
    __tablename__ = 'measurements'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    point_id = Column(UUID(as_uuid=True), ForeignKey('points.id', ondelete='CASCADE'), nullable=False)
    measurement_timestamp = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    point_name = Column(Text, nullable=False)
    unit = Column(Text)
    value = Column(Numeric(14, 6), nullable=False)
    quality = Column(Integer)
    schema_version = Column(Integer, nullable=False, default=1)
    meta_hash = Column(Text)


class DeviceStatus(enum.Enum):
    READY = "ready"
    DEGRADED = "degraded"
    ERROR = "error"


class DeviceState(Base):
    __tablename__ = "device_state"

    id = Column(UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), primary_key=True)
    last_seen_ts = Column(DateTime(timezone=True), nullable=False)
    last_upload_ts = Column(DateTime(timezone=True))
    queue_depth = Column(Integer)
    agent_version = Column(Text)
    poll_interval_s = Column(Integer)

    cpu_pct = Column(Numeric(5, 2))
    disk_free_gb = Column(Numeric(10, 2))

    status = Column(Enum(DeviceStatus, name="device_status"), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now())

    device = relationship("Device", back_populates="state")
