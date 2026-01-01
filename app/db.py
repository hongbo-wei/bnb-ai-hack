from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import DATABASE_URL


def create_db_engine():
    return create_engine(DATABASE_URL, pool_pre_ping=True)


ENGINE = create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=ENGINE)
