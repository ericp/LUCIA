from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Ruta absoluta al archivo SQLite
DB_PATH = "/Users/eric/Documents/Masters Degree/M10.-TFM/LUCIA/data/db.sqlite3"
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Crear motor de base de datos
engine = create_engine(DATABASE_URL)

# Crear sesión
SessionLocal = sessionmaker(bind=engine)

# Base para modelos
Base = declarative_base()

# Modelo para detecciones
class Detection(Base):
    __tablename__ = "detections"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)   # nombre de archivo (si quieres guardarlo)
    label = Column(String, index=True)      # etiqueta detectada
    confidence = Column(Float)              # confianza del model


class UserLabel(Base):
    __tablename__ = "user_labels"
    id = Column(Integer, primary_key=True, index=True)
    detection_id = Column(Integer, index=True)  # referencia a detections
    label = Column(String, index=True)          # etiqueta corregida

# Crear las tablas si no existen
Base.metadata.create_all(bind=engine)

