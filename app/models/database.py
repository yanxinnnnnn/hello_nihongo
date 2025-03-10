from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

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
    
class UserSession(Base):
    __tablename__ = 'user_sessions'

    session_id = Column(String(255), primary_key=True)
    open_id = Column(String(255), nullable=False)
    avatar = Column(Text, nullable=True)
    nick_name = Column(String(255), nullable=True)
    expires_at = Column(DateTime, nullable=False)

    def is_valid(self) -> bool:
        """检查会话是否有效"""
        return self.expires_at > datetime.now()

Base.metadata.create_all(bind=engine)