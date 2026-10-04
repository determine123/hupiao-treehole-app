import hashlib, hmac, secrets, time
from typing import Annotated
from fastapi import Depends, HTTPException, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select, delete
from redis import Redis, RedisError
from .config import settings
from .db import database
from .models import User, RateBucket

bearer = HTTPBearer(auto_error=False)
redis = (
    Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_connect_timeout=3,
        socket_timeout=3,
    )
    if settings.redis_url
    else None
)


def digest(value):
    return hmac.new(
        settings.token_pepper.encode(), value.encode(), hashlib.sha256
    ).hexdigest()


def identity(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    session=Depends(database),
):
    if not credentials:
        raise HTTPException(401, "请先接受约定并创建匿名身份")
    user = session.scalar(
        select(User).where(User.secret_hash == digest(credentials.credentials))
    )
    if not user:
        raise HTTPException(401, "匿名凭据无效，请重新创建身份")
    if user.banned:
        raise HTTPException(403, "该匿名身份已暂停使用")
    return user


def admin(token: Annotated[str | None, Header(alias="X-Admin-Token")] = None):
    if (
        not settings.admin_token
        or not token
        or not secrets.compare_digest(token, settings.admin_token)
    ):
        raise HTTPException(403, "管理员凭据无效")
    return True


def conflict_insert(table, session):
    if session.bind.dialect.name == "postgresql":
        from sqlalchemy.dialects.postgresql import insert
    else:
        from sqlalchemy.dialects.sqlite import insert
    return insert(table)


def rate(session, key, limit=30, seconds=600):
    bucket = int(time.time()) // seconds
    key = digest(key) + ":" + str(bucket)
    if redis:
        script = "local n=redis.call('INCR',KEYS[1]); if n==1 then redis.call('EXPIRE',KEYS[1],ARGV[1]) end; return n"
        try:
            count = redis.eval(script, 1, "rate:" + key, seconds + 1)
        except RedisError:
            raise HTTPException(503, "服务暂时繁忙，请稍后重试")
    else:
        statement = conflict_insert(RateBucket, session).values(
            key=key, count=1, expires=int(time.time()) + seconds
        )
        statement = statement.on_conflict_do_update(
            index_elements=[RateBucket.key], set_={"count": RateBucket.count + 1}
        ).returning(RateBucket.count)
        count = session.scalar(statement)
        session.execute(delete(RateBucket).where(RateBucket.expires < int(time.time())))
        session.commit()
    if count > limit:
        raise HTTPException(
            429, "操作过于频繁，请稍后再试", headers={"Retry-After": str(seconds)}
        )


def bootstrap_key(request: Request):
    return "signup:" + (request.client.host if request.client else "unknown")
