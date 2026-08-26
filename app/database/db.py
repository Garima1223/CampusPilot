import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Configurable via env var so this runs out-of-the-box without any local
# MySQL setup (SQLite file, zero config) but can point at real MySQL/Postgres
# in production just by setting DATABASE_URL, e.g.:
#   DATABASE_URL=mysql+pymysql://root:panda@localhost/campuspilot
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./campuspilot.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
