from sre_lab.token_store import TokenStore


def test_token_store_issues_hashes_and_revokes(tmp_path):
    store = TokenStore(tmp_path / "tokens.json")
    issued = store.issue("alice-agent", ttl_days=7, owner="alice", created_by="admin")
    assert issued["token"].startswith("sre_agent_")
    assert store.verify(issued["token"])
    listed = store.list()[0]
    assert listed["name"] == "alice-agent"
    assert listed["owner"] == "alice"
    assert listed["created_by"] == "admin"
    assert listed["last_used_at"] is not None
    assert listed["use_count"] == 1
    assert "hash" not in listed
    assert store.revoke(issued["token_id"])
    assert not store.verify(issued["token"])


def test_token_store_enforces_scopes(tmp_path):
    store = TokenStore(tmp_path / "tokens.json")
    issued = store.issue("read-only", scopes=["evidence:read"])
    assert store.verify(issued["token"], "evidence:read")
    assert not store.verify(issued["token"], "run:create")


def test_token_store_rejects_unknown_scope(tmp_path):
    store = TokenStore(tmp_path / "tokens.json")
    try:
        store.issue("unsafe", scopes=["cluster:admin"])
    except ValueError as exc:
        assert "unsupported" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("unknown scope should be rejected")
