import os
from sqlmodel import SQLModel, create_engine, Session

# 환경 변수에서 DATABASE_URL을 조회하고, 없을 경우 로컬 SQLite DB 사용
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./meeting_room.db")

# Railway / Heroku 등 호스팅 서비스의 postgres:// 호환 처리
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# SQLite 사용 시 멀티 스레드 접속 허용 옵션 적용
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)

def init_db():
    """데이터베이스 테이블 생성"""
    SQLModel.metadata.create_all(engine)

def get_session():
    """데이터베이스 세션 의존성 제공"""
    with Session(engine) as session:
        yield session
