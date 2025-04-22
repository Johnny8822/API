# database.py
import os
from dotenv import load_dotenv
# Removed unnecessary imports from flask and psycopg2
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker # Import async components
from sqlalchemy.ext.declarative import declarative_base # Still use declarative_base from here

# Import Base from this file for models.py
Base = declarative_base()

load_dotenv() # Load variables from .env file

DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_SERVER = os.getenv("DB_SERVER", "localhost")
DB_NAME = os.getenv("DB_NAME")

# --- Connection string for PostgreSQL using asyncpg ---
# Change the dialect prefix
SQLALCHEMY_DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_SERVER}/{DB_NAME}"

# --- SQLAlchemy Async Engine ---
# Use create_async_engine
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=20,      # Increase from default 5
    max_overflow=10    # Allow extra temporary connections
    # Add echo=True for debugging SQL queries if needed
    # echo=True
)

# --- Async SessionLocal class ---
# Use async_sessionmaker
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession, # Specify the async session class
    expire_on_commit=False # Good practice for async sessions
)

# --- Async Dependency function to get a DB session ---
# This function must also be async
async def get_db():
    # Use async with for the session
    async with AsyncSessionLocal() as db:
        try:
            yield db # Provides the async session to the endpoint
            await db.commit() # Commit the transaction (or handle commits explicitly in routes)
        except Exception:
            await db.rollback() # Rollback on error
            raise # Re-raise the exception
        # finally:
            # async with handles closing automatically

# --- Async function to create tables (run this once at startup) ---
async def create_tables():
    print("Attempting to create database tables asynchronously...")
    async with engine.begin() as conn:
        # Use run_sync because Base.metadata.create_all is synchronous
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables checked/created.")

# NOTE: The models.py file will now need to import Base from this database.py file
# Make sure models.py has: from database import Base