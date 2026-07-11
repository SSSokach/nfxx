from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    avatar = Column(String, default="")

class Contact(Base):
    __tablename__ = "contacts"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    avatar = Column(String, default="")
    is_group = Column(Boolean, default=False)

class UserContact(Base):
    __tablename__ = "user_contacts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    contact_id = Column(Integer, ForeignKey("contacts.id"))
    user = relationship("User", backref="user_contacts")
    contact = relationship("Contact", backref="user_contacts")

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"))
    contact_id = Column(Integer, ForeignKey("contacts.id"))
    content = Column(Text)
    message_type = Column(String, default="text")
    file_id = Column(Integer, ForeignKey("files.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    sender = relationship("User", backref="messages")
    contact = relationship("Contact", backref="messages")
    file = relationship("File", backref="messages")

class File(Base):
    __tablename__ = "files"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    content = Column(Text)
    file_type = Column(String, default="markdown")
    owner_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    owner = relationship("User", backref="files")
