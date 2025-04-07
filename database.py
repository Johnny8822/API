# database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os
from dotenv import load_dotenv

load_dotenv() # Load variables from .env file

DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_SERVER = os.getenv("DB_SERVER", "localhost")
DB_NAME = os.getenv("DB_NAME")

# Connection string for PostgreSQL
SQLALCHEMY_DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_SERVER}/{DB_NAME}"

# SQLAlchemy engine: The heart of the connection
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# SessionLocal class: Each instance will be a database session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for declarative models: Our DB models will inherit from this
Base = declarative_base()

# Dependency function to get a DB session in API endpoints
def get_db():
    db = SessionLocal()
    try:
        yield db # Provides the session to the endpoint
    finally:
        db.close() # Ensures the session is closed afterwards