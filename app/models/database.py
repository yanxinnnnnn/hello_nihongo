from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = 'sqlite:///./translations.db'

engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class TranslationRecord(Base):
    __tablename__ = 'translations'
    
    id = Column(Integer, primary_key=True, index=True)
    original_sentence = Column(String, index=True, nullable=False)
    translated_sentence = Column(String, index=True, nullable=False)
    furigana = Column(String, index=True, nullable=False)
    grammar = Column(Text, nullable=False)
    
Base.metadata.create_all(bind=engine)