import uuid, time
from sqlalchemy import (
    String,
    Text,
    BigInteger,
    Boolean,
    ForeignKey,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base


def uid():
    return str(uuid.uuid4())


def now():
    return int(time.time() * 1000)


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    secret_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created: Mapped[int] = mapped_column(BigInteger, default=now)
    terms: Mapped[str] = mapped_column(String(32))
    banned: Mapped[bool] = mapped_column(Boolean, default=False)


class Post(Base):
    __tablename__ = "posts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(80))
    body: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(32))
    created: Mapped[int] = mapped_column(BigInteger, default=now)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    likes: Mapped[int] = mapped_column(BigInteger, default=0)
    replies: Mapped[int] = mapped_column(BigInteger, default=0)
    __table_args__ = (
        Index("posts_feed", "status", "created", "id"),
        Index("posts_category_feed", "status", "category", "created", "id"),
        Index("posts_owner_feed", "owner", "created", "id"),
    )


class Comment(Base):
    __tablename__ = "comments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    post: Mapped[str] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"))
    owner: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    body: Mapped[str] = mapped_column(Text)
    created: Mapped[int] = mapped_column(BigInteger, default=now)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    __table_args__ = (Index("comments_thread", "post", "status", "created", "id"),)


class Like(Base):
    __tablename__ = "likes"
    post: Mapped[str] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True
    )
    owner: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    __table_args__ = (Index("likes_owner", "owner", "post"),)


class Block(Base):
    __tablename__ = "blocks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    target: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    created: Mapped[int] = mapped_column(BigInteger, default=now)
    __table_args__ = (UniqueConstraint("owner", "target"),)


class Report(Base):
    __tablename__ = "reports"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    target_type: Mapped[str] = mapped_column(String(16))
    target_id: Mapped[str] = mapped_column(String(36))
    reason: Mapped[str] = mapped_column(String(300))
    created: Mapped[int] = mapped_column(BigInteger, default=now)
    status: Mapped[str] = mapped_column(String(16), default="open")
    __table_args__ = (
        UniqueConstraint("owner", "target_type", "target_id"),
        Index("reports_queue", "status", "created"),
    )


class Feedback(Base):
    __tablename__ = "feedback"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(16))
    body: Mapped[str] = mapped_column(Text)
    device: Mapped[str] = mapped_column(String(150))
    app_version: Mapped[str] = mapped_column(String(30))
    created: Mapped[int] = mapped_column(BigInteger, default=now)
    status: Mapped[str] = mapped_column(String(16), default="new")
    response: Mapped[str] = mapped_column(Text, default="")
    __table_args__ = (Index("feedback_queue", "status", "created"),)


class Audit(Base):
    __tablename__ = "audit"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    target: Mapped[str] = mapped_column(String(36))
    action: Mapped[str] = mapped_column(String(30))
    note: Mapped[str] = mapped_column(String(300))
    created: Mapped[int] = mapped_column(BigInteger, default=now)


class RateBucket(Base):
    __tablename__ = "rate_buckets"
    key: Mapped[str] = mapped_column(String(120), primary_key=True)
    count: Mapped[int] = mapped_column(BigInteger)
    expires: Mapped[int] = mapped_column(BigInteger, index=True)
