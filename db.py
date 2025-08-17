# db.py
from sqlalchemy import create_engine
from models import Base

def get_engine(db_url: str = "sqlite:///recipes.db"):
    return create_engine(db_url, future=True, echo=False)

def init_db(engine=None):
    engine = engine or get_engine()
    Base.metadata.create_all(engine)
    return engine
