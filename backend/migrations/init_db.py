"""
Database Initialization Script

Run this script to create all tables in Supabase if they don't exist.

Usage:
    python -m backend.migrations.init_db

Or from the backend directory:
    python migrations/init_db.py
"""
import asyncio
import logging
import sys
from pathlib import Path

# Add backend directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# SQL for creating tables (for Supabase)
CREATE_TABLES_SQL = """
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create ic_specifications table
CREATE TABLE IF NOT EXISTS ic_specifications (
    id SERIAL PRIMARY KEY,
    part_number VARCHAR(100) UNIQUE NOT NULL,
    manufacturer VARCHAR(100),
    pin_count INTEGER NOT NULL,
    package_type VARCHAR(50),
    description TEXT,
    datasheet_url VARCHAR(500),
    datasheet_path VARCHAR(500),
    voltage_min FLOAT,
    voltage_max FLOAT,
    operating_temp_min FLOAT,
    operating_temp_max FLOAT,
    electrical_specs JSONB DEFAULT '{}',
    source VARCHAR(50) DEFAULT 'MANUAL',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create scan_history table
CREATE TABLE IF NOT EXISTS scan_history (
    id SERIAL PRIMARY KEY,
    scan_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    ocr_text_raw TEXT,
    part_number_detected VARCHAR(100),
    part_number_verified VARCHAR(100),
    status VARCHAR(20) NOT NULL,
    confidence_score FLOAT,
    detected_pins INTEGER,
    expected_pins INTEGER,
    manufacturer_detected VARCHAR(100),
    action_required VARCHAR(20) DEFAULT 'NONE',
    has_bottom_scan BOOLEAN DEFAULT FALSE,
    match_details JSONB,
    failure_reasons JSONB,
    message TEXT,
    was_manual_override BOOLEAN DEFAULT FALSE,
    operator_note TEXT,
    scanned_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- Create datasheet_queue table
CREATE TABLE IF NOT EXISTS datasheet_queue (
    id SERIAL PRIMARY KEY,
    part_number VARCHAR(100) UNIQUE NOT NULL,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_scanned_at TIMESTAMPTZ DEFAULT NOW(),
    scan_count INTEGER DEFAULT 1,
    status VARCHAR(20) DEFAULT 'PENDING',
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create fake_registry table
CREATE TABLE IF NOT EXISTS fake_registry (
    id SERIAL PRIMARY KEY,
    part_number VARCHAR(100) UNIQUE NOT NULL,
    source VARCHAR(20) NOT NULL,
    reason TEXT,
    reported_by VARCHAR(100),
    scrape_attempts INTEGER DEFAULT 0,
    manufacturers_checked JSONB,
    added_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create sync_jobs table
CREATE TABLE IF NOT EXISTS sync_jobs (
    id SERIAL PRIMARY KEY,
    job_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    status VARCHAR(20) NOT NULL DEFAULT 'IDLE',
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    total_items INTEGER DEFAULT 0,
    processed_items INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    failed_count INTEGER DEFAULT 0,
    fake_count INTEGER DEFAULT 0,
    current_item VARCHAR(100),
    error_message TEXT,
    log JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create settings table
CREATE TABLE IF NOT EXISTS settings (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) UNIQUE NOT NULL,
    value TEXT NOT NULL,
    value_type VARCHAR(20) DEFAULT 'STRING',
    description TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by VARCHAR(100)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_ic_specs_part_number ON ic_specifications(part_number);
CREATE INDEX IF NOT EXISTS idx_ic_specs_manufacturer ON ic_specifications(manufacturer);
CREATE INDEX IF NOT EXISTS idx_scan_history_scan_id ON scan_history(scan_id);
CREATE INDEX IF NOT EXISTS idx_scan_history_status ON scan_history(status);
CREATE INDEX IF NOT EXISTS idx_scan_history_scanned_at ON scan_history(scanned_at);
CREATE INDEX IF NOT EXISTS idx_datasheet_queue_status ON datasheet_queue(status);
CREATE INDEX IF NOT EXISTS idx_fake_registry_part_number ON fake_registry(part_number);
CREATE INDEX IF NOT EXISTS idx_sync_jobs_job_id ON sync_jobs(job_id);
CREATE INDEX IF NOT EXISTS idx_sync_jobs_status ON sync_jobs(status);
"""

# Default settings to insert
DEFAULT_SETTINGS = [
    ("datasheet_folder_path", "/data/datasheets", "STRING", "Directory where PDF datasheets are stored"),
    ("auto_queue_unknown", "true", "BOOLEAN", "Automatically add unknown ICs to sync queue"),
    ("ocr_confidence_threshold", "70.0", "FLOAT", "Minimum OCR confidence to accept (0-100)"),
    ("scan_history_retention_days", "365", "INTEGER", "Days to keep scan history before cleanup"),
    ("enable_auto_cleanup", "true", "BOOLEAN", "Automatically delete old scan records"),
    ("pin_detection_model", "yolov8", "STRING", "Vision model for pin counting"),
    ("ocr_model", "paddleocr", "STRING", "OCR engine to use"),
    ("max_scrape_retries", "3", "INTEGER", "Max retries before marking IC as fake"),
    ("scrape_timeout_seconds", "5", "INTEGER", "Timeout for each scrape request"),
]

# Sample IC data
SAMPLE_ICS = [
    ("LM555", "Texas Instruments", 8, "DIP", "Precision Timer IC capable of producing accurate time delays or oscillation", 4.5, 16.0, 0, 70, '{"timing_accuracy": "1%", "output_current": "200mA", "supply_current": "3mA"}'),
    ("NE555", "Texas Instruments", 8, "DIP", "General Purpose Single Bipolar Timer", 4.5, 16.0, 0, 70, '{"timing_accuracy": "1%", "output_current": "200mA"}'),
    ("ATMEGA328P", "Microchip", 32, "QFN", "8-bit AVR Microcontroller with 32KB Flash", 1.8, 5.5, -40, 85, '{"flash_memory": "32KB", "sram": "2KB", "eeprom": "1KB", "max_frequency": "20MHz"}'),
    ("LM7805", "Texas Instruments", 3, "TO-220", "Positive 5V Voltage Regulator", 7.0, 35.0, 0, 125, '{"output_voltage": "5V", "output_current": "1.5A", "dropout_voltage": "2V"}'),
    ("LM317", "Texas Instruments", 3, "TO-220", "Adjustable Positive Voltage Regulator", 3.0, 40.0, 0, 125, '{"output_voltage_range": "1.25V-37V", "output_current": "1.5A"}'),
    ("74HC595", "NXP", 16, "DIP", "8-bit Serial-In Parallel-Out Shift Register", 2.0, 6.0, -40, 125, '{"max_frequency": "100MHz", "output_current": "35mA"}'),
    ("LM741", "Texas Instruments", 8, "DIP", "General Purpose Operational Amplifier", 5.0, 18.0, 0, 70, '{"gain_bandwidth": "1MHz", "slew_rate": "0.5V/us", "input_offset_voltage": "1mV"}'),
    ("CD4017", "Texas Instruments", 16, "DIP", "Decade Counter/Divider with 10 Decoded Outputs", 3.0, 15.0, -40, 85, '{"max_frequency": "5MHz", "propagation_delay": "250ns"}'),
]


async def create_tables(engine):
    """Create all tables using raw SQL."""
    from sqlalchemy import text
    
    logger.info("Creating database tables...")
    
    async with engine.begin() as conn:
        # Execute the CREATE TABLES SQL
        for statement in CREATE_TABLES_SQL.split(";"):
            statement = statement.strip()
            if statement:
                try:
                    await conn.execute(text(statement))
                except Exception as e:
                    logger.warning(f"Statement might already exist or failed: {e}")
    
    logger.info("Tables created successfully!")


async def insert_default_settings(session_maker):
    """Insert default settings if not exist."""
    from sqlalchemy import text
    
    logger.info("Inserting default settings...")
    
    async with session_maker() as session:
        for key, value, value_type, description in DEFAULT_SETTINGS:
            try:
                await session.execute(
                    text("""
                        INSERT INTO settings (key, value, value_type, description)
                        VALUES (:key, :value, :value_type, :description)
                        ON CONFLICT (key) DO NOTHING
                    """),
                    {"key": key, "value": value, "value_type": value_type, "description": description}
                )
            except Exception as e:
                logger.warning(f"Could not insert setting {key}: {e}")
        
        await session.commit()
    
    logger.info("Default settings inserted!")


async def insert_sample_ics(session_maker):
    """Insert sample IC data if not exist."""
    from sqlalchemy import text
    
    logger.info("Inserting sample IC data...")
    
    async with session_maker() as session:
        for part_number, manufacturer, pin_count, package_type, description, v_min, v_max, t_min, t_max, specs in SAMPLE_ICS:
            try:
                await session.execute(
                    text("""
                        INSERT INTO ic_specifications 
                        (part_number, manufacturer, pin_count, package_type, description, 
                         voltage_min, voltage_max, operating_temp_min, operating_temp_max, 
                         electrical_specs, source)
                        VALUES (:part_number, :manufacturer, :pin_count, :package_type, :description,
                                :v_min, :v_max, :t_min, :t_max, :specs::jsonb, 'MANUAL')
                        ON CONFLICT (part_number) DO NOTHING
                    """),
                    {
                        "part_number": part_number,
                        "manufacturer": manufacturer,
                        "pin_count": pin_count,
                        "package_type": package_type,
                        "description": description,
                        "v_min": v_min,
                        "v_max": v_max,
                        "t_min": t_min,
                        "t_max": t_max,
                        "specs": specs,
                    }
                )
            except Exception as e:
                logger.warning(f"Could not insert IC {part_number}: {e}")
        
        await session.commit()
    
    logger.info("Sample IC data inserted!")


async def verify_tables(session_maker):
    """Verify that all tables exist and log counts."""
    from sqlalchemy import text
    
    logger.info("Verifying tables...")
    
    async with session_maker() as session:
        tables = ["ic_specifications", "scan_history", "datasheet_queue", "fake_registry", "sync_jobs", "settings"]
        
        for table in tables:
            try:
                result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                logger.info(f"  ✓ {table}: {count} rows")
            except Exception as e:
                logger.error(f"  ✗ {table}: {e}")


async def main():
    """Run database initialization."""
    # Import here to avoid import-time errors
    from core.config import settings
    from core.database import engine, async_session_maker
    
    logger.info("=" * 60)
    logger.info("Drishti IC Backend - Database Initialization")
    logger.info("=" * 60)
    
    # Check if DATABASE_URL is set
    if not settings.DATABASE_URL:
        logger.error("DATABASE_URL is not set!")
        logger.error("Please set it in your .env file or environment variables.")
        logger.error("Example: DATABASE_URL=postgresql://postgres:password@db.xxx.supabase.co:5432/postgres")
        logger.error("")
        logger.error("Steps:")
        logger.error("1. Copy backend/env.example to backend/.env")
        logger.error("2. Fill in your Supabase credentials")
        logger.error("3. Run this script again")
        return
    
    logger.info(f"Database URL: {settings.DATABASE_URL[:50]}...")
    
    try:
        # Create tables
        await create_tables(engine)
        
        # Insert defaults
        await insert_default_settings(async_session_maker)
        await insert_sample_ics(async_session_maker)
        
        # Verify
        await verify_tables(async_session_maker)
        
        logger.info("=" * 60)
        logger.info("Database initialization complete!")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
