from conftest import user, post, approve, ADMIN
from app.db import Session, engine
from app.models import Post, User
from sqlalchemy import select, event, text


def test_consent_and_auth(client):
    assert client.post("/session", json={"accepted_terms": "old"}).status_code == 422
    assert client.get("/posts").status_code == 401
    assert client.get("/admin/queue").status_code == 403
    a = user(client)
    assert client.get("/me", headers=a).status_code == 200
    assert client.get("/ready").status_code == 200


def test_review_flow_and_reply_counts(client):
    a, b = user(client), user(client)
    p = post(client, a)
    assert p["status"] == "pending" and "owner" not in p
    assert client.get("/posts", headers=b).json()["posts"] == []
    assert client.get("/posts/" + p["id"], headers=b).status_code == 404
    approve(client, "post", p["id"])
    r = client.post(
        "/posts/" + p["id"] + "/comments", headers=b, json={"body": "回复正在等待审核"}
    )
    assert r.status_code == 201, r.text
    c = r.json()
    assert c["status"] == "pending"
    assert (
        client.get("/posts/" + p["id"] + "/comments", headers=a).json()["comments"]
        == []
    )
    approve(client, "comment", c["id"])
    approve(client, "comment", c["id"])
    assert client.get("/posts/" + p["id"], headers=a).json()["post"]["replies"] == 1
    assert client.delete("/comments/" + c["id"], headers=a).status_code == 404
    assert client.delete("/comments/" + c["id"], headers=b).status_code == 200
    assert client.get("/posts/" + p["id"], headers=a).json()["post"]["replies"] == 0


def test_votes_blocks_reports(client):
    a, b = user(client), user(client)
    p = post(client, a)
    approve(client, "post", p["id"])
    path = "/posts/" + p["id"] + "/like"
    for _ in range(2):
        assert client.put(path, headers=b, json={"liked": True}).json()["likes"] == 1
    assert len(client.get("/posts?view=liked", headers=b).json()["posts"]) == 1
    assert (
        client.post(
            "/reports",
            headers=b,
            json={
                "target_type": "post",
                "target_id": p["id"],
                "reason": "请审核测试内容",
            },
        ).status_code
        == 201
    )
    assert len(client.get("/admin/reports", headers=ADMIN).json()) == 1
    assert (
        client.post("/blocks", headers=b, json={"target_id": p["id"]}).status_code
        == 201
    )
    assert client.get("/posts", headers=b).json()["posts"] == []
    assert client.get("/posts/" + p["id"], headers=b).status_code == 404
    block = client.get("/blocks", headers=b).json()[0]["id"]
    client.delete("/blocks/" + block, headers=a)
    assert len(client.get("/blocks", headers=b).json()) == 1
    client.delete("/blocks/" + block, headers=b)
    assert client.put(path, headers=b, json={"liked": False}).json()["likes"] == 0


def test_feedback_loop_and_identity_deletion(client):
    a, b = user(client), user(client)
    p = post(client, a)
    approve(client, "post", p["id"])
    client.put("/posts/" + p["id"] + "/like", headers=b, json={"liked": True})
    c = client.post(
        "/posts/" + p["id"] + "/comments", headers=b, json={"body": "删除匿名身份测试"}
    ).json()
    approve(client, "comment", c["id"])
    f = client.post(
        "/feedback",
        headers=b,
        json={
            "kind": "idea",
            "body": "希望改进字体大小选项",
            "device": "test",
            "app_version": "1.0.0",
        },
    ).json()
    assert client.get("/feedback", headers=a).json() == []
    assert (
        client.put(
            "/admin/feedback/" + f["id"],
            headers=ADMIN,
            json={"status": "planned", "response": "已加入内测改进计划"},
        ).status_code
        == 200
    )
    assert (
        client.get("/feedback", headers=b).json()[0]["response"] == "已加入内测改进计划"
    )
    assert client.delete("/me", headers=b).status_code == 200
    assert client.get("/me", headers=b).status_code == 401
    p2 = client.get("/posts/" + p["id"], headers=a).json()["post"]
    assert p2["likes"] == 0 and p2["replies"] == 0


def test_cursor_feed_and_query_budget(client):
    a = user(client)
    with Session() as session:
        u = session.scalar(select(User))
        session.add_all(
            [
                Post(
                    owner=u.id,
                    title="分页测试" + str(i),
                    body="测试分页和索引查询",
                    category="情绪树洞",
                    created=1700000000000 + i,
                    status="active",
                )
                for i in range(43)
            ]
        )
        session.commit()
    statements = []

    def count(conn, cursor, statement, parameters, context, many):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", count)
    try:
        page = client.get("/posts", headers=a).json()
    finally:
        event.remove(engine, "before_cursor_execute", count)
    assert len(statements) <= 3, statements
    ids = [p["id"] for p in page["posts"]]
    while page["next_cursor"]:
        page = client.get(
            "/posts", headers=a, params={"cursor": page["next_cursor"]}
        ).json()
        ids += [p["id"] for p in page["posts"]]
    assert len(ids) == len(set(ids)) == 43
    assert client.get("/posts?cursor=broken", headers=a).status_code == 422
    assert client.get("/posts?view=unknown", headers=a).status_code == 422
    if engine.dialect.name == "sqlite":
        with engine.connect() as c:
            plan = c.execute(
                text(
                    "EXPLAIN QUERY PLAN SELECT id FROM posts WHERE status='active' ORDER BY created DESC,id DESC LIMIT 20"
                )
            ).all()
            assert any("posts_feed" in str(row) for row in plan)


def test_validation_and_rate_limit(client):
    a = user(client)
    assert (
        client.post(
            "/posts",
            headers=a,
            json={
                "title": "测试",
                "body": "联系电话 13812345678",
                "category": "生活求助",
            },
        ).status_code
        == 422
    )
    for _ in range(3):
        post(client, a)
    assert (
        client.post(
            "/posts",
            headers=a,
            json={
                "title": "第四条",
                "body": "应该被频率限制的帖子",
                "category": "生活求助",
            },
        ).status_code
        == 429
    )
    assert client.post("/posts", headers=a, content=b"x" * 33000).status_code == 413
    assert client.delete("/posts/nonexistent", headers=a).status_code == 404
