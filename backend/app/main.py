import base64, json, secrets, re, uuid, time
from fastapi import FastAPI, Depends, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from sqlalchemy import select, update, delete, exists, and_, or_, case, text, func
from .config import settings
from .db import database
from .models import User, Post, Comment, Like, Block, Report, Feedback, Audit, now
from .security import (
    identity,
    admin,
    digest,
    rate,
    bootstrap_key,
    conflict_insert,
    redis,
)
from .schemas import (
    TERMS,
    CATEGORIES,
    Consent,
    CreatePost,
    CreateComment,
    Vote,
    ReportInput,
    BlockInput,
    FeedbackInput,
    ModerateInput,
    FeedbackReply,
)

app = FastAPI(
    title="沪漂树洞 API",
    version="1.0.0",
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url=None,
)
if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )


@app.middleware("http")
async def bounded_requests(request: Request, call_next):
    if request.method in {"POST", "PUT", "PATCH"}:
        size = 0
        parts = []
        async for part in request.stream():
            size += len(part)
            if size > 32768:
                from fastapi.responses import JSONResponse

                return JSONResponse({"detail": "请求内容过长"}, status_code=413)
            parts.append(part)
        request._body = b"".join(parts)
    started = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Request-ID"] = str(uuid.uuid4())
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Server-Timing"] = (
        f"app;dur={(time.perf_counter() - started) * 1000:.1f}"
    )
    return response


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready(session=Depends(database)):
    session.execute(text("SELECT 1"))
    if redis:
        redis.ping()
    return {"status": "ready"}


@app.get("/config")
def config():
    return {
        "terms_version": TERMS,
        "categories": CATEGORIES,
        "support_email": settings.support_email,
        "moderation": "pre-publication"
        if settings.moderate_before_publish
        else "post-publication",
        "version": "1.0.0",
    }


@app.post("/session", status_code=201)
def signup(b: Consent, request: Request, session=Depends(database)):
    if b.accepted_terms != TERMS:
        raise HTTPException(422, "请先阅读并接受当前社区约定")
    rate(session, bootstrap_key(request), 10, 3600)
    token = secrets.token_hex(32)
    user = User(secret_hash=digest(token), terms=TERMS)
    session.add(user)
    session.commit()
    return {"token": token, "terms_version": TERMS}


@app.get("/me")
def me(user=Depends(identity)):
    return {"terms_version": user.terms, "created": user.created}


def safety(value):
    if re.search(r"(?<!\d)1[3-9]\d{9}(?!\d)", value):
        raise HTTPException(422, "内容可能包含手机号，请隐去个人信息后再发布")


def unblocked(model, user):
    return ~exists(
        select(Block.id).where(Block.owner == user.id, Block.target == model.owner)
    )


def visible_post(session, id, user):
    p = session.scalar(
        select(Post).where(
            Post.id == id,
            or_(
                Post.status == "active",
                and_(Post.owner == user.id, Post.status.in_(["pending", "hidden"])),
            ),
            unblocked(Post, user),
        )
    )
    if not p:
        raise HTTPException(404, "讨论不存在或暂不可见")
    return p


def serialize_post(p, user, liked=False):
    return {
        "id": p.id,
        "title": p.title,
        "body": p.body,
        "category": p.category,
        "created": p.created,
        "status": p.status,
        "likes": p.likes,
        "replies": p.replies,
        "liked": liked,
        "mine": p.owner == user.id,
        "author": "过客 " + digest(p.owner + ":" + p.id)[:6].upper(),
    }


def serialize_comment(c, user, p):
    return {
        "id": c.id,
        "body": c.body,
        "created": c.created,
        "status": c.status,
        "mine": c.owner == user.id,
        "isOp": c.owner == p.owner,
        "author": "过客 " + digest(c.owner + ":" + p.id)[:6].upper(),
    }


def decode_cursor(cursor):
    try:
        created, id = json.loads(
            base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4))
        )
        if not isinstance(created, int) or not isinstance(id, str) or len(id) != 36:
            raise ValueError()
        return created, id
    except Exception:
        raise HTTPException(422, "分页标识无效")


def encode_cursor(row):
    return (
        base64.urlsafe_b64encode(json.dumps([row.created, row.id]).encode())
        .decode()
        .rstrip("=")
    )


@app.get("/posts")
def posts(
    category: str = "",
    view: str = "all",
    q: str = Query(default="", max_length=100),
    cursor: str = Query(default="", max_length=180),
    limit: int = Query(default=20, ge=1, le=50),
    user=Depends(identity),
    session=Depends(database),
):
    statement = select(Post).where(
        Post.status.in_(["active", "pending", "hidden"])
        if view == "mine"
        else Post.status == "active",
        unblocked(Post, user),
    )
    if view == "mine":
        statement = statement.where(Post.owner == user.id)
    elif view == "liked":
        statement = statement.where(
            exists(select(Like.post).where(Like.post == Post.id, Like.owner == user.id))
        )
    elif view == "replied":
        statement = statement.where(
            exists(
                select(Comment.id).where(
                    Comment.post == Post.id,
                    Comment.owner == user.id,
                    Comment.status.in_(["active", "pending"]),
                )
            )
        )
    elif view != "all":
        raise HTTPException(422, "筛选项无效")
    if category:
        if category not in CATEGORIES:
            raise HTTPException(422, "版块无效")
        statement = statement.where(Post.category == category)
    if q:
        statement = statement.where(
            or_(
                Post.title.contains(q, autoescape=True),
                Post.body.contains(q, autoescape=True),
            )
        )
    if cursor:
        created, id = decode_cursor(cursor)
        statement = statement.where(
            or_(Post.created < created, and_(Post.created == created, Post.id < id))
        )
    rows = session.scalars(
        statement.order_by(Post.created.desc(), Post.id.desc()).limit(limit + 1)
    ).all()
    ids = [p.id for p in rows[:limit]]
    liked = (
        set(
            session.scalars(
                select(Like.post).where(Like.owner == user.id, Like.post.in_(ids))
            ).all()
        )
        if ids
        else set()
    )
    return {
        "posts": [serialize_post(p, user, p.id in liked) for p in rows[:limit]],
        "next_cursor": encode_cursor(rows[limit - 1]) if len(rows) > limit else None,
    }


@app.post("/posts", status_code=201)
def create_post(b: CreatePost, user=Depends(identity), session=Depends(database)):
    safety(b.title + "\n" + b.body)
    rate(session, "post:" + user.id, 3)
    p = Post(
        owner=user.id,
        **b.model_dump(),
        status="pending" if settings.moderate_before_publish else "active",
    )
    session.add(p)
    session.commit()
    return serialize_post(p, user)


@app.get("/posts/{id}")
def read_post(id: str, user=Depends(identity), session=Depends(database)):
    p = visible_post(session, id, user)
    liked = session.get(Like, (id, user.id)) is not None
    return {"post": serialize_post(p, user, liked)}


@app.get("/posts/{id}/comments")
def comments(
    id: str,
    cursor: str = Query(default="", max_length=180),
    user=Depends(identity),
    session=Depends(database),
):
    p = visible_post(session, id, user)
    statement = select(Comment).where(
        Comment.post == id,
        or_(
            Comment.status == "active",
            and_(Comment.owner == user.id, Comment.status == "pending"),
        ),
        unblocked(Comment, user),
    )
    if cursor:
        created, cid = decode_cursor(cursor)
        statement = statement.where(
            or_(
                Comment.created > created,
                and_(Comment.created == created, Comment.id > cid),
            )
        )
    rows = session.scalars(
        statement.order_by(Comment.created, Comment.id).limit(51)
    ).all()
    return {
        "comments": [serialize_comment(c, user, p) for c in rows[:50]],
        "next_cursor": encode_cursor(rows[49]) if len(rows) > 50 else None,
    }


@app.post("/posts/{id}/comments", status_code=201)
def comment(
    id: str, b: CreateComment, user=Depends(identity), session=Depends(database)
):
    p = visible_post(session, id, user)
    if p.status != "active":
        raise HTTPException(409, "暂不可回复这条讨论")
    safety(b.body)
    rate(session, "comment:" + user.id, 15)
    c = Comment(
        post=id,
        owner=user.id,
        body=b.body,
        status="pending" if settings.moderate_before_publish else "active",
    )
    session.add(c)
    if c.status == "active":
        session.execute(
            update(Post).where(Post.id == id).values(replies=Post.replies + 1)
        )
    session.commit()
    return serialize_comment(c, user, p)


@app.put("/posts/{id}/like")
def like(id: str, b: Vote, user=Depends(identity), session=Depends(database)):
    p = visible_post(session, id, user)
    if p.status != "active":
        raise HTTPException(409, "暂不可共鸣这条讨论")
    rate(session, "like:" + user.id, 60)
    if b.liked:
        result = session.execute(
            conflict_insert(Like, session)
            .values(post=id, owner=user.id)
            .on_conflict_do_nothing(index_elements=[Like.post, Like.owner])
            .returning(Like.post)
        )
        if result.scalar_one_or_none() is not None:
            session.execute(
                update(Post).where(Post.id == id).values(likes=Post.likes + 1)
            )
    else:
        result = session.execute(
            delete(Like).where(Like.post == id, Like.owner == user.id).returning(Like.post)
        )
        if result.scalar_one_or_none() is not None:
            session.execute(
                update(Post)
                .where(Post.id == id)
                .values(likes=case((Post.likes > 0, Post.likes - 1), else_=0))
            )
    session.commit()
    session.refresh(p)
    return {"liked": b.liked, "likes": p.likes}


@app.delete("/posts/{id}")
def delete_post(id: str, user=Depends(identity), session=Depends(database)):
    p = session.get(Post, id)
    if not p or p.owner != user.id:
        raise HTTPException(404, "无法删除这条讨论")
    session.delete(p)
    session.commit()
    return {"ok": True}


@app.delete("/comments/{id}")
def delete_comment(id: str, user=Depends(identity), session=Depends(database)):
    c = session.get(Comment, id)
    if not c or c.owner != user.id:
        raise HTTPException(404, "无法删除这条回复")
    if c.status == "active":
        session.execute(
            update(Post)
            .where(Post.id == c.post)
            .values(replies=case((Post.replies > 0, Post.replies - 1), else_=0))
        )
    session.delete(c)
    session.commit()
    return {"ok": True}


def target(session, b, user):
    model = Post if b.target_type == "post" else Comment
    obj = session.get(model, b.target_id)
    if not obj:
        raise HTTPException(404, "内容不存在")
    visible_post(session, obj.id if model is Post else obj.post, user)
    if model is Comment and obj.status != "active" and obj.owner != user.id:
        raise HTTPException(404, "回复不可见")
    return obj


@app.post("/reports", status_code=201)
def report(b: ReportInput, user=Depends(identity), session=Depends(database)):
    obj = target(session, b, user)
    if obj.owner == user.id:
        raise HTTPException(422, "自己的内容可以直接删除")
    rate(session, "report:" + user.id, 20)
    session.execute(
        conflict_insert(Report, session)
        .values(
            id=str(uuid.uuid4()),
            owner=user.id,
            **b.model_dump(),
            created=now(),
            status="open",
        )
        .on_conflict_do_nothing(
            index_elements=[Report.owner, Report.target_type, Report.target_id]
        )
    )
    session.commit()
    return {"ok": True}


@app.post("/blocks", status_code=201)
def block(b: BlockInput, user=Depends(identity), session=Depends(database)):
    obj = target(session, b, user)
    if obj.owner == user.id:
        raise HTTPException(422, "不能屏蔽自己的内容")
    rate(session, "block:" + user.id, 30)
    session.execute(
        conflict_insert(Block, session)
        .values(id=str(uuid.uuid4()), owner=user.id, target=obj.owner, created=now())
        .on_conflict_do_nothing(index_elements=[Block.owner, Block.target])
    )
    session.commit()
    return {"ok": True}


@app.get("/blocks")
def blocks(user=Depends(identity), session=Depends(database)):
    rows = session.scalars(
        select(Block)
        .where(Block.owner == user.id)
        .order_by(Block.created.desc())
        .limit(200)
    ).all()
    return [{"id": b.id, "created": b.created} for b in rows]


@app.delete("/blocks/{id}")
def unblock(id: str, user=Depends(identity), session=Depends(database)):
    session.execute(delete(Block).where(Block.id == id, Block.owner == user.id))
    session.commit()
    return {"ok": True}


@app.post("/feedback", status_code=201)
def feedback(b: FeedbackInput, user=Depends(identity), session=Depends(database)):
    rate(session, "feedback:" + user.id, 5, 3600)
    f = Feedback(owner=user.id, **b.model_dump())
    session.add(f)
    session.commit()
    return {"id": f.id, "status": f.status}


@app.get("/feedback")
def my_feedback(user=Depends(identity), session=Depends(database)):
    return [
        {
            "id": f.id,
            "body": f.body,
            "kind": f.kind,
            "status": f.status,
            "response": f.response,
            "created": f.created,
        }
        for f in session.scalars(
            select(Feedback)
            .where(Feedback.owner == user.id)
            .order_by(Feedback.created.desc())
            .limit(100)
        )
    ]


@app.delete("/me")
def delete_identity(user=Depends(identity), session=Depends(database)):
    # Recompute affected counters inside the same deletion transaction.
    liked = session.scalars(select(Like.post).where(Like.owner == user.id)).all()
    replied = session.scalars(
        select(Comment.post)
        .where(Comment.owner == user.id, Comment.status == "active")
        .distinct()
    ).all()
    for pid in set(liked):
        session.execute(
            update(Post)
            .where(Post.id == pid)
            .values(likes=case((Post.likes > 0, Post.likes - 1), else_=0))
        )
    for pid in replied:
        n = session.scalar(
            select(func.count())
            .select_from(Comment)
            .where(
                Comment.post == pid,
                Comment.owner == user.id,
                Comment.status == "active",
            )
        )
        session.execute(
            update(Post)
            .where(Post.id == pid)
            .values(replies=case((Post.replies >= n, Post.replies - n), else_=0))
        )
    session.delete(user)
    session.commit()
    return {"ok": True}


@app.get("/admin/queue", dependencies=[Depends(admin)])
def queue(session=Depends(database)):
    posts = session.scalars(
        select(Post).where(Post.status == "pending").order_by(Post.created).limit(100)
    ).all()
    comments = session.scalars(
        select(Comment)
        .where(Comment.status == "pending")
        .order_by(Comment.created)
        .limit(100)
    ).all()
    return [
        {
            "type": "post",
            "id": p.id,
            "title": p.title,
            "body": p.body,
            "category": p.category,
            "created": p.created,
        }
        for p in posts
    ] + [
        {
            "type": "comment",
            "id": c.id,
            "post": c.post,
            "body": c.body,
            "created": c.created,
        }
        for c in comments
    ]


@app.post("/admin/moderate", dependencies=[Depends(admin)])
def moderate(b: ModerateInput, session=Depends(database)):
    model = Post if b.target_type == "post" else Comment
    obj = session.scalar(select(model).where(model.id == b.target_id).with_for_update())
    if not obj:
        raise HTTPException(404, "内容不存在")
    previous = obj.status
    obj.status = "active" if b.decision == "approve" else "hidden"
    if isinstance(obj, Comment) and previous != obj.status:
        delta = 1 if obj.status == "active" else -1 if previous == "active" else 0
        if delta:
            session.execute(
                update(Post)
                .where(Post.id == obj.post)
                .values(
                    replies=case(
                        (Post.replies + delta >= 0, Post.replies + delta), else_=0
                    )
                )
            )
    session.add(Audit(target=obj.id, action=b.decision, note=b.note))
    if b.decision == "hide":
        session.execute(
            update(Report)
            .where(Report.target_id == obj.id, Report.target_type == b.target_type)
            .values(status="resolved")
        )
    session.commit()
    return {"ok": True, "status": obj.status}


@app.get("/admin/reports", dependencies=[Depends(admin)])
def reports(session=Depends(database)):
    result = []
    for r in session.scalars(
        select(Report)
        .where(Report.status == "open")
        .order_by(Report.created)
        .limit(100)
    ):
        target = session.get(Post if r.target_type == "post" else Comment, r.target_id)
        result.append(
            {
                "id": r.id,
                "type": r.target_type,
                "target_id": r.target_id,
                "reason": r.reason,
                "body": target.body if target else "内容已删除",
                "created": r.created,
            }
        )
    return result


@app.get("/admin/feedback", dependencies=[Depends(admin)])
def feedback_queue(session=Depends(database)):
    return [
        {
            "id": f.id,
            "body": f.body,
            "device": f.device,
            "kind": f.kind,
            "app_version": f.app_version,
            "status": f.status,
            "response": f.response,
            "created": f.created,
        }
        for f in session.scalars(
            select(Feedback).order_by(Feedback.created.desc()).limit(100)
        )
    ]


@app.put("/admin/feedback/{id}", dependencies=[Depends(admin)])
def feedback_reply(id: str, b: FeedbackReply, session=Depends(database)):
    f = session.get(Feedback, id)
    if not f:
        raise HTTPException(404, "反馈不存在")
    f.status = b.status
    f.response = b.response
    session.add(Audit(target=id, action="feedback", note=b.status))
    session.commit()
    return {"ok": True}


@app.get("/admin", response_class=HTMLResponse)
def admin_page():
    from pathlib import Path

    return Path(__file__).with_name("admin.html").read_text(encoding="utf-8")


@app.delete("/admin/reports/{id}", dependencies=[Depends(admin)])
def dismiss_report(id: str, session=Depends(database)):
    report = session.get(Report, id)
    if not report:
        raise HTTPException(404, "举报不存在")
    report.status = "resolved"
    session.add(Audit(target=id, action="dismiss_report", note="已检查并关闭举报"))
    session.commit()
    return {"ok": True}
