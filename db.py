from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import settings

engine = create_engine(settings.database_url, echo=settings.sql_echo)
SessionLocal = sessionmaker(engine)
