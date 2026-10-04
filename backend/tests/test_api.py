from conftest import user, post, approve, ADMIN
from app.db import Session, engine
from app.models import Post, User, Report, Comment
from sqlalchemy import select, event, text


def test_stale_duplicate_comment_deletion_does_not_remove_another_reply_count(client):
    from app.main import delete_comment
    from fastapi import HTTPException
    import pytest
    from types import SimpleNamespace

    a, b = user(client), user(client)
    p = post(client, a)
    approve(client, "post", p["id"])
    replies = []
    for _ in range(2):
        response = client.post(
            "/posts/" + p["id"] + "/comments",
            headers=b,
            json={"body": "并发删除计数回归测试"},
        )
        assert response.status_code == 201
        replies.append(response.json())
        approve(client, "comment", replies[-1]["id"])
    with Session() as first, Session() as second:
        # Both requests already read the same row before the first one commits.
        earlier = first.get(Comment, replies[0]["id"])
        stale = second.get(Comment, replies[0]["id"])
        author = SimpleNamespace(id=earlier.owner)
        assert stale.status == "active"
        assert delete_comment(earlier.id, author, first) == {"ok": True}
        with pytest.raises(HTTPException) as error:
            delete_comment(stale.id, author, second)
        assert error.value.status_code == 404
    assert client.get("/posts/" + p["id"], headers=a).json()["post"]["replies"] == 1


def test_comment_deletion_uses_current_status_after_moderation(client):
    from app.main import delete_comment
    from types import SimpleNamespace

    a, b = user(client), user(client)
    p = post(client, a)
    approve(client, "post", p["id"])
    response = client.post(
        "/posts/" + p["id"] + "/comments",
        headers=b,
        json={"body": "审核和删除交错执行回归测试"},
    )
    assert response.status_code == 201
    cid = response.json()["id"]
    with Session() as deletion:
        stale = deletion.get(Comment, cid)
        assert stale.status == "pending"
        approve(client, "comment", cid)
        assert client.get("/posts/" + p["id"], headers=a).json()["post"]["replies"] == 1
        assert delete_comment(cid, SimpleNamespace(id=stale.owner), deletion) == {
            "ok": True
        }
    assert client.get("/posts/" + p["id"], headers=a).json()["post"]["replies"] == 0


def test_deleted_content_reports_leave_queue_without_closing_unrelated_reports(client):
    a, b, reporter = user(client), user(client), user(client)
    p, retained = post(client, a), post(client, b)
    approve(client, "post", p["id"])
    approve(client, "post", retained["id"])
    c = client.post(
        "/posts/" + p["id"] + "/comments", headers=b, json={"body": "被连带删除的回复"}
    ).json()
    approve(client, "comment", c["id"])
    for kind, target in [
        ("post", p["id"]),
        ("comment", c["id"]),
        ("post", retained["id"]),
    ]:
        assert (
            client.post(
                "/reports",
                headers=reporter,
                json={
                    "target_type": kind,
                    "target_id": target,
                    "reason": "请检查这条内容",
                },
            ).status_code
            == 201
        )
    assert client.delete("/posts/" + p["id"], headers=b).status_code == 404
    assert len(client.get("/admin/reports", headers=ADMIN).json()) == 3
    assert client.delete("/posts/" + p["id"], headers=a).status_code == 200
    queue = client.get("/admin/reports", headers=ADMIN).json()
    assert [r["target_id"] for r in queue] == [retained["id"]]
    with Session() as session:
        assert session.get(Comment, c["id"]) is None
        assert set(
            session.scalars(
                select(Report.status).where(Report.target_id.in_([p["id"], c["id"]]))
            )
        ) == {"resolved"}


def test_comment_and_identity_deletion_resolve_external_reports(client):
    a, b, reporter = user(client), user(client), user(client)
    own, retained = post(client, a), post(client, b)
    for p in [own, retained]:
        approve(client, "post", p["id"])
    comments = []
    for p, author in [(retained, a), (retained, a), (own, b)]:
        c = client.post(
            "/posts/" + p["id"] + "/comments",
            headers=author,
            json={"body": "身份删除和单条回复删除测试"},
        ).json()
        approve(client, "comment", c["id"])
        comments.append(c)
    for kind, target in [("post", own["id"]), ("post", retained["id"])] + [
        ("comment", c["id"]) for c in comments
    ]:
        assert (
            client.post(
                "/reports",
                headers=reporter,
                json={
                    "target_type": kind,
                    "target_id": target,
                    "reason": "请检查这条内容",
                },
            ).status_code
            == 201
        )
    assert client.delete("/comments/" + comments[0]["id"], headers=a).status_code == 200
    assert len(client.get("/admin/reports", headers=ADMIN).json()) == 4
    assert client.delete("/me", headers=a).status_code == 200
    assert [
        r["target_id"] for r in client.get("/admin/reports", headers=ADMIN).json()
    ] == [retained["id"]]
    assert (
        client.get("/posts/" + retained["id"], headers=b).json()["post"]["replies"] == 0
    )
    with Session() as session:
        rows = session.scalars(select(Report)).all()
        assert (
            len(rows) == 5
        )  # Keep report records; content removal is not an admin decision.
        assert sum(r.status == "resolved" for r in rows) == 4


def test_legacy_missing_report_targets_do_not_fill_admin_queue(client):
    a, b = user(client), user(client)
    p = post(client, a)
    approve(client, "post", p["id"])
    assert (
        client.post(
            "/reports",
            headers=b,
            json={
                "target_type": "post",
                "target_id": p["id"],
                "reason": "仍然需要处理的举报",
            },
        ).status_code
        == 201
    )
    with Session() as session:
        owner = session.scalar(
            select(User.id).where(User.id != session.get(Post, p["id"]).owner)
        )
        import uuid

        session.add_all(
            [
                Report(
                    owner=owner,
                    target_type="post",
                    target_id=str(uuid.uuid4()),
                    reason="历史已删除内容",
                    created=0,
                )
                for _ in range(101)
            ]
        )
        session.commit()
    assert [
        r["target_id"] for r in client.get("/admin/reports", headers=ADMIN).json()
    ] == [p["id"]]


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
    for _ in range(2):
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


def test_discovery_sorting_and_visibility(client):
    from app.models import now

    b = user(client)
    ids = [post(client, user(client))["id"] for _ in range(5)]
    for pid in ids[:4]:
        approve(client, "post", pid)
    with Session() as session:
        rows = [session.get(Post, pid) for pid in ids]
        rows[0].likes, rows[0].replies = 1, 2
        rows[1].likes, rows[1].replies = 4, 0
        rows[2].created = now() - 8 * 24 * 60 * 60 * 1000
        rows[2].likes = 100
        rows[4].likes = 1000  # Pending content must never enter the public ranking.
        session.commit()
    hot = client.get("/posts?sort=hot", headers=b).json()
    assert [p["id"] for p in hot["posts"]] == [ids[0], ids[1], ids[3]]
    assert hot["next_cursor"] is None
    waiting = client.get("/posts?sort=unanswered&limit=1", headers=b).json()
    seen = [p["id"] for p in waiting["posts"]]
    while waiting["next_cursor"]:
        waiting = client.get(
            "/posts",
            params={"sort": "unanswered", "limit": 1, "cursor": waiting["next_cursor"]},
            headers=b,
        ).json()
        seen.extend(p["id"] for p in waiting["posts"])
    assert set(seen) == set(ids[1:4]) and len(seen) == 3
    assert client.get("/posts?sort=unknown", headers=b).status_code == 422
    assert client.get("/posts?sort=hot&cursor=bad", headers=b).status_code == 422
    client.post("/blocks", headers=b, json={"target_id": ids[0]})
    assert [
        p["id"] for p in client.get("/posts?sort=hot", headers=b).json()["posts"]
    ] == [ids[1], ids[3]]


def test_review_queue_includes_parent_context_only_for_admin(client):
    a = user(client)
    p = post(client, a)
    approve(client, "post", p["id"])
    r = client.post(
        "/posts/" + p["id"] + "/comments",
        headers=a,
        json={"body": "需要结合原帖判断的回复"},
    )
    assert r.status_code == 201
    assert client.get("/admin/queue", headers=a).status_code == 403
    queue = client.get("/admin/queue", headers=ADMIN).json()
    comment = next(x for x in queue if x["id"] == r.json()["id"])
    assert comment["parent_title"] == p["title"]
    assert comment["parent_status"] == "active"
    assert comment["parent_excerpt"] == p["body"][:500]
    assert "owner" not in comment and "secret_hash" not in comment
    with Session() as session:
        parent = session.get(Post, p["id"])
        parent.body = "长" * 1500
        session.commit()
    comment = client.get("/admin/queue", headers=ADMIN).json()[0]
    assert len(comment["parent_excerpt"]) == 500


def test_moderation_history_separates_private_notes_and_owner_access(client):
    a, b = user(client), user(client)
    pa, pb = post(client, a), post(client, b)

    def decide(pid, decision, reason):
        r = client.post(
            "/admin/moderate",
            headers=ADMIN,
            json={
                "target_type": "post",
                "target_id": pid,
                "decision": decision,
                "note": "内部记录：不得给作者查看",
                "public_reason": reason,
            },
        )
        assert r.status_code == 200, r.text

    decide(pa["id"], "hide", "请移除可识别的个人信息")
    decide(pa["id"], "approve", "已复核通过")
    decide(pb["id"], "hide", "另一位作者的说明")
    assert client.get("/admin/audit", headers=a).status_code == 403
    mine = client.get("/moderation", headers=a).json()["records"]
    assert len(mine) == 2 and all(x["target_id"] == pa["id"] for x in mine)
    assert {x["reason"] for x in mine} == {"请移除可识别的个人信息", "已复核通过"}
    assert all("note" not in x for x in mine)
    assert "内部记录" not in str(mine) and "另一位作者" not in str(mine)
    assert len(client.get("/moderation", headers=b).json()["records"]) == 1
    seen = []
    cursor = ""
    while True:
        page = client.get(
            "/admin/audit",
            headers=ADMIN,
            params={"limit": 1, **({"cursor": cursor} if cursor else {})},
        ).json()
        seen.extend(x["id"] for x in page["records"])
        cursor = page["next_cursor"]
        if not cursor:
            break
    assert len(seen) == len(set(seen)) == 3
    filtered = client.get(
        "/admin/audit", headers=ADMIN, params={"target": pa["id"]}
    ).json()["records"]
    assert len(filtered) == 2 and all("内部记录" in x["note"] for x in filtered)
    assert client.get("/admin/audit?target=short", headers=ADMIN).status_code == 422
    assert client.get("/moderation?cursor=broken", headers=a).status_code == 422
    assert client.delete("/posts/" + pa["id"], headers=a).status_code == 200
    assert client.get("/moderation", headers=a).json()["records"] == []


def test_hidden_reply_and_legacy_reason_privacy(client):
    from app.models import Audit, now

    a, b = user(client), user(client)
    p = post(client, a)
    approve(client, "post", p["id"])
    r = client.post(
        "/posts/" + p["id"] + "/comments",
        headers=b,
        json={"body": "这个回复属于第二位作者"},
    ).json()
    response = client.post(
        "/admin/moderate",
        headers=ADMIN,
        json={
            "target_type": "comment",
            "target_id": r["id"],
            "decision": "hide",
            "note": "内部记录",
            "public_reason": "请补充事实来源",
        },
    )
    assert response.status_code == 200
    assert (
        client.get("/posts/" + p["id"] + "/comments", headers=a).json()["comments"]
        == []
    )
    own = client.get(
        "/posts/" + p["id"] + "/comments?include_hidden=true", headers=b
    ).json()["comments"]
    assert (
        client.get("/posts/" + p["id"] + "/comments", headers=b).json()["comments"]
        == []
    )
    assert (
        client.get(
            "/posts/" + p["id"] + "/comments?include_hidden=true", headers=a
        ).json()["comments"]
        == []
    )
    assert len(own) == 1 and own[0]["status"] == "hidden"
    records = client.get("/moderation", headers=b).json()["records"]
    assert (
        records[0]["reason"] == "请补充事实来源"
        and records[0]["target_type"] == "comment"
    )
    with Session() as session:
        session.add(
            Audit(target=p["id"], action="hide", note="旧的内部秘密", created=now())
        )
        session.commit()
    public = client.get("/moderation", headers=a).json()["records"]
    assert all(not x["reason"] for x in public) and "旧的内部秘密" not in str(public)
    unsafe = client.post(
        "/admin/moderate",
        headers=ADMIN,
        json={
            "target_type": "post",
            "target_id": p["id"],
            "decision": "hide",
            "note": "内部记录",
            "public_reason": "联系 13800138000",
        },
    )
    assert unsafe.status_code == 422
    assert (
        client.get("/posts/" + p["id"], headers=b).json()["post"]["status"] == "active"
    )
