import enum
import uuid
from sqlalchemy import (
    Column, Integer, Boolean, Numeric, Text, ForeignKey, DateTime, String,
    UniqueConstraint, Enum, Index
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()


class Site(Base):
    __tablename__ = 'sites'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    display_name = Column(String(64), unique=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    devices = relationship(
        "Device",
        back_populates="site",
        cascade="all, delete-orphan",
        passive_deletes=True,
        single_parent=True,
    )
    points = relationship(
        "Point",
        back_populates="site", 
        cascade="all, delete-orphan", 
        passive_deletes=True, 
        single_parent=True
    )


class Device(Base):
    __tablename__ = 'devices'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id = Column(UUID(as_uuid=True), ForeignKey('sites.id', ondelete='CASCADE'), nullable=False)
    model = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    site = relationship("Site", back_populates="devices")
    state = relationship(
        "DeviceState", 
        uselist=False, 
        back_populates="device", 
        cascade="all, delete-orphan", 
        passive_deletes=True, 
        single_parent=True
    )


class Point(Base):
    __tablename__ = 'points'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)  # UUID PK
    site_id = Column(UUID(as_uuid=True), ForeignKey('sites.id', ondelete='CASCADE'), nullable=False)


    # BACnet fields
    name = Column(String(255), nullable=False) # Object_Name
    object_type = Column(String(255), nullable=False) # e.g., "Analog Value"
    object_instance = Column(Integer, nullable=False) # e.g., 9
    description = Column(Text, nullable=True) # BACnet Description
    cov_increment = Column(Numeric(14, 6), nullable=True) # COV_Increment


    # Generic metadata
    unit = Column(String(64), nullable=False)
    tags = Column(MutableDict.as_mutable(JSONB), nullable=False, default=dict)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (UniqueConstraint('site_id', 'object_type', 'object_instance', name='uq_points_site_type_instance'),)

    site = relationship("Site", back_populates="points")
    metadata_history = relationship("PointMetadataHistory", back_populates="point", cascade="all, delete-orphan", passive_deletes=True, single_parent=True)
    validation_rules = relationship("ValidationRule", back_populates="point", cascade="all, delete-orphan", passive_deletes=True, single_parent=True)
    measurements = relationship("Measurement", back_populates="point", cascade="all, delete-orphan", passive_deletes=True, single_parent=True)

class PointMetadataHistory(Base):
    __tablename__ = 'point_metadata_history'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    point_id = Column(UUID(as_uuid=True), ForeignKey('points.id', ondelete='CASCADE'), nullable=False)
    effective_from = Column(DateTime(timezone=True), nullable=False)
    unit = Column(String(64), nullable=False)
    tags = Column(MutableDict.as_mutable(JSONB), nullable=False, default=dict)
    meta_hash = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    point = relationship("Point", back_populates="metadata_history")


class Measurement(Base):
    __tablename__ = 'measurements'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    point_id = Column(UUID(as_uuid=True), ForeignKey('points.id', ondelete='CASCADE'), nullable=False)

    measurement_timestamp = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


    point_name = Column(String(255), nullable=False)
    unit = Column(String(64))
    value = Column(Numeric(14, 6), nullable=False)
    
    # BACnet extensions
    status_flags = Column(MutableDict.as_mutable(JSONB), nullable=True, default=dict)   # e.g. { "in_alarm":0, "fault":0, ... }
    event_state = Column(Integer, nullable=True)  # BACnet Event_State
    reliability = Column(Integer, nullable=True)  # BACnet Reliability (enum int)
    priority_array = Column(MutableDict.as_mutable(JSONB), nullable=True, default=dict) # Optional priority values
    source_timestamp = Column(DateTime(timezone=True), nullable=True) # Device timestamp if diff from ingestion

    __table_args__ = (UniqueConstraint('point_id', 'measurement_timestamp', name='uq_point_measurement_time'),)

    quality = Column(Integer)
    schema_version = Column(Integer, nullable=False, default=1)
    meta_hash = Column(Text)

    point = relationship("Point", back_populates="measurements")

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
    agent_version = Column(String(32))
    poll_interval_s = Column(Integer)

    cpu_pct = Column(Numeric(5, 2))
    disk_free_gb = Column(Numeric(10, 2))

    status = Column(Enum(DeviceStatus, name="device_status"), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    device = relationship("Device", back_populates="state")

Index('ix_measurements_point_time', Measurement.point_id, Measurement.measurement_timestamp.desc())
Index('ix_measurements_time', Measurement.measurement_timestamp.desc())
Index('ix_devices_site', Device.site_id)
Index('ix_points_site', Point.site_id)
Index('ix_points_site_type_instance',
      Point.site_id,
      Point.object_type,
      Point.object_instance)
 