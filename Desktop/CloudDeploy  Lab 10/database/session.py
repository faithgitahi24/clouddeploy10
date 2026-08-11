import os

from dotenv import load_dotenv
from sqlmodel import SQLModel, Session, create_engine


# Load variables from .env
load_dotenv()


# Get database URL
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./database.db"
)


# SQLite needs this setting when used with FastAPI
connect_args = {}

if DATABASE_URL.startswith("sqlite"):
    connect_args = {
        "check_same_thread": False
    }


# Create database engine
engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args=connect_args
)


# Create database tables
def create_db():
    SQLModel.metadata.create_all(engine)


# Provide database session to FastAPI endpoints
def get_session():
    with Session(engine) as session:
        yield session