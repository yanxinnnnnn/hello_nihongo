import uuid
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.database import UserSession
from app.config import config

SESSION_EXPIRATION_DAYS = config.get('session.expiration_days', 7)

def create_user_session(db: Session, open_id: str, avatar: str, nick_name: str) -> str:
    """创建新的用户会话并存储到数据库，返回 session_id"""
    session_id = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(days=SESSION_EXPIRATION_DAYS)
    
    user_session = UserSession(
        session_id=session_id,
        open_id=open_id,
        avatar=avatar,
        nick_name=nick_name,
        expires_at=expires_at
    )
    db.add(user_session)
    db.commit()
    
    return session_id

def get_user_session(db: Session, session_id: str) -> UserSession:
    """根据 session_id 获取有效的用户会话"""
    user_session = db.query(UserSession).filter_by(session_id=session_id).first()
    if user_session and user_session.expires_at > datetime.utcnow():
        return user_session
    return None

def delete_user_session(db: Session, session_id: str):
    """删除用户会话"""
    db.query(UserSession).filter_by(session_id=session_id).delete()
    db.commit()