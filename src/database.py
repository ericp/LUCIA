from datetime import datetime, timezone
import os
from pathlib import Path

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(
    os.environ.get("LUCIA_DB_PATH", PROJECT_ROOT / "data" / "db.sqlite3")
).expanduser().resolve()
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite:///{DB_PATH}"
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class Detection(Base):
    __tablename__ = "detections"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)
    label = Column(String, index=True)
    confidence = Column(Float)
    scanned_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    recognized_text = Column(Text, nullable=True)
    text_confidence = Column(Float, nullable=True)


class UserLabel(Base):
    __tablename__ = "user_labels"

    id = Column(Integer, primary_key=True, index=True)
    detection_id = Column(Integer, index=True)
    label = Column(String, index=True)


def _migrate_existing_database() -> None:
    """Add new detection metadata without deleting existing records."""
    columns = {column["name"] for column in inspect(engine).get_columns("detections")}
    missing_columns = {"scanned_at", "recognized_text", "text_confidence"} - columns
    if not missing_columns:
        return

    with engine.begin() as connection:
        if "scanned_at" in missing_columns:
            images_dir = PROJECT_ROOT / "data" / "images"
            database_timestamp = datetime.fromtimestamp(
                DB_PATH.stat().st_mtime,
                timezone.utc,
            )
            connection.execute(text("ALTER TABLE detections ADD COLUMN scanned_at DATETIME"))
            records = connection.execute(text("SELECT id, filename FROM detections")).mappings()

            for record in records:
                image_path = images_dir / Path(record["filename"] or "").name
                timestamp = (
                    datetime.fromtimestamp(image_path.stat().st_mtime, timezone.utc)
                    if image_path.is_file()
                    else database_timestamp
                )
                connection.execute(
                    text("UPDATE detections SET scanned_at = :scanned_at WHERE id = :id"),
                    {"scanned_at": timestamp.replace(tzinfo=None), "id": record["id"]},
                )

            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_detections_scanned_at "
                    "ON detections (scanned_at)"
                )
            )

        if "recognized_text" in missing_columns:
            connection.execute(text("ALTER TABLE detections ADD COLUMN recognized_text TEXT"))

        if "text_confidence" in missing_columns:
            connection.execute(text("ALTER TABLE detections ADD COLUMN text_confidence FLOAT"))


Base.metadata.create_all(bind=engine)
_migrate_existing_database()
