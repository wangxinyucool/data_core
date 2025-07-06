import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool, QueuePool

# 数据库配置
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///feedback.db')

# 如果是Render的PostgreSQL，需要处理URL格式
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

# 创建数据库引擎
if DATABASE_URL.startswith('sqlite'):
    # 本地开发使用SQLite
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
else:
    # 生产环境使用PostgreSQL，优化连接池配置
    engine = create_engine(
        DATABASE_URL,
        poolclass=QueuePool,
        pool_size=10,           # 连接池大小
        max_overflow=20,        # 最大溢出连接数
        pool_timeout=30,        # 连接超时时间
        pool_recycle=3600,      # 连接回收时间（1小时）
        pool_pre_ping=True      # 连接前ping检查
    )

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 数据库依赖
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 初始化数据库
def init_db():
    from .models import Base
    Base.metadata.create_all(bind=engine) 