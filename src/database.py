from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Absolute path to SQLite file
DB_PATH = "/Users/eric/Documents/Masters Degree/M10.-TFM/LUCIA/data/db.sqlite3"
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Create database engine
engine = create_engine(DATABASE_URL)

# Create the session
SessionLocal = sessionmaker(bind=engine)

# Base for models
Base = declarative_base()

# Model for detections
class Detection(Base):
    __tablename__ = "detections"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)   
    label = Column(String, index=True)      
    confidence = Column(Float)              


class UserLabel(Base):
    __tablename__ = "user_labels"
    id = Column(Integer, primary_key=True, index=True)
    detection_id = Column(Integer, index=True)  
    label = Column(String, index=True)          

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

