"""
Database models for IC verification system
"""
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from typing import Dict, List, Optional

Base = declarative_base()


class Manufacturer(Base):
    """Manufacturer information"""
    __tablename__ = "manufacturers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    short_name = Column(String(20), unique=True, nullable=False)
    website = Column(String(200))
    datasheet_base_url = Column(String(300))
    logo_reference_path = Column(String(300))  
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    ics = relationship("IC", back_populates="manufacturer")


class IC(Base):
    """Integrated Circuit specifications"""
    __tablename__ = "ics"

    id = Column(Integer, primary_key=True, index=True)
    part_number = Column(String(50), unique=True, nullable=False)
    manufacturer_id = Column(Integer, ForeignKey("manufacturers.id"), nullable=False)

    operating_voltage_min = Column(Float)
    operating_voltage_max = Column(Float)
    operating_voltage_unit = Column(String(10), default="V")

    current_rating = Column(Float)
    current_unit = Column(String(10), default="A")

    temperature_min = Column(Float)
    temperature_max = Column(Float)
    temperature_unit = Column(String(10), default="°C")

    pin_count = Column(Integer)
    package_type = Column(String(50))
    dimensions = Column(JSON)  # {"length": x, "width": y, "height": z, "unit": "mm"}

    marking_specifications = Column(JSON) 
    font_specifications = Column(JSON)  
    logo_requirements = Column(JSON)  

    datasheet_url = Column(String(500))
    datasheet_path = Column(String(300))  
    datasheet_last_updated = Column(DateTime)

    other_specs = Column(JSON)  

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    manufacturer = relationship("Manufacturer", back_populates="ics")
    verification_results = relationship("VerificationResult", back_populates="ic")


class VerificationResult(Base):
    """Results of IC verification process"""
    __tablename__ = "verification_results"

    id = Column(Integer, primary_key=True, index=True)
    ic_id = Column(Integer, ForeignKey("ics.id"), nullable=False)

    image_path = Column(String(300))
    video_session_id = Column(String(100))  

    detected_part_number = Column(String(50))
    detected_manufacturer = Column(String(100))
    detected_text = Column(Text)
    confidence_scores = Column(JSON)  # {"ocr": 0.95, "logo": 0.87, "font": 0.92}

    logo_match_score = Column(Float)
    font_similarity_score = Column(Float)
    marking_accuracy_score = Column(Float)
    overall_confidence = Column(Float)

    is_genuine = Column(Boolean, default=False)
    authenticity_reasons = Column(JSON)  

    analysis_results = Column(JSON) 

    created_at = Column(DateTime, default=datetime.utcnow)
    processing_time_seconds = Column(Float)

    ic = relationship("IC", back_populates="verification_results")


class VideoSession(Base):
    """Video streaming sessions for live camera feed"""
    __tablename__ = "video_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), unique=True, nullable=False)
    device_id = Column(String(100))  
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime)
    duration_seconds = Column(Float)
    frame_count = Column(Integer, default=0)
    status = Column(String(20), default="active")  

    resolution = Column(String(20))  
    fps = Column(Float)


class DatasheetCache(Base):
    """Cache for downloaded datasheets"""
    __tablename__ = "datasheet_cache"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(500), unique=True, nullable=False)
    local_path = Column(String(300), nullable=False)
    downloaded_at = Column(DateTime, default=datetime.utcnow)
    last_accessed = Column(DateTime, default=datetime.utcnow)
    file_size_bytes = Column(Integer)
    checksum = Column(String(64))  



from config.settings import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)


def init_database():
    """Initialize database with default data"""
    create_tables()

    db = SessionLocal()
    try:
        for manufacturer_name, data in settings.supported_manufacturers.items():
            existing = db.query(Manufacturer).filter_by(name=manufacturer_name).first()
            if not existing:
                manufacturer = Manufacturer(
                    name=manufacturer_name,
                    short_name=data["short_name"],
                    website=data["website"],
                    datasheet_base_url=data["datasheet_base_url"]
                )
                db.add(manufacturer)

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error initializing database: {e}")
    finally:
        db.close()
