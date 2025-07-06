from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timezone, timedelta

Base = declarative_base()

# 中国时区 (UTC+8)
CHINA_TZ = timezone(timedelta(hours=8))

def china_now():
    """获取中国时区的当前时间"""
    return datetime.now(CHINA_TZ)

class Feedback(Base):
    __tablename__ = 'feedback'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    rating = Column(Integer, nullable=False)  # 1-5星评分
    suggestion = Column(Text, nullable=False)  # 用户建议
    timestamp = Column(DateTime, default=china_now, nullable=False)
    device_info = Column(JSON)  # 设备信息
    ip_address = Column(String(45))  # IP地址
    user_agent = Column(String(500))  # 用户代理
    created_at = Column(DateTime, default=china_now)
    is_read = Column(Boolean, default=False)
    
    def __repr__(self):
        return f"<Feedback(id={self.id}, rating={self.rating}, timestamp={self.timestamp})>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'rating': self.rating,
            'suggestion': self.suggestion,
            'timestamp': self.timestamp.strftime('%Y-%m-%dT%H:%M:%S+08:00') if self.timestamp else None,
            'device_info': self.device_info,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent
        }

class Message(Base):
    __tablename__ = 'messages'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(200), nullable=False)
    subject = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    device_info = Column(String(500))
    created_at = Column(DateTime, default=china_now)
    is_read = Column(Boolean, default=False)
    is_replied = Column(Boolean, default=False)
    
    def __repr__(self):
        return f"<Message(id={self.id}, name={self.name}, subject={self.subject})>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'subject': self.subject,
            'content': self.content,
            'device_info': self.device_info,
            'created_at': self.created_at.strftime('%Y-%m-%dT%H:%M:%S+08:00') if self.created_at else None,
            'is_read': self.is_read,
            'is_replied': self.is_replied
        } 