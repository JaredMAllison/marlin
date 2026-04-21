import json
import pytest
from pathlib import Path
from gv_gateway.users import load_users


@pytest.fixture
def users_file(tmp_path):
    f = tmp_path / "users.json"
    f.write_text(json.dumps({
        "jared": {
            "key_file": str(tmp_path / "jared.key"),
            "email": "jared@gmail.com",
            "broadcast_name": "Jared (SMS)",
            "ntfy_topic": "jared-topic",
            "routes": ["inbox", "sos", "ntfy"],
        },
        "family": {
            "key_file": str(tmp_path / "family.key"),
            "email": None,
            "broadcast_name": "Family",
            "ntfy_topic": None,
            "routes": ["sos"],
        },
    }))
    return f


def test_load_users_returns_all_users(users_file):
    users = load_users(users_file)
    assert len(users) == 2
    ids = {u.user_id for u in users}
    assert ids == {"jared", "family"}


def test_load_users_jared_fields(users_file, tmp_path):
    users = load_users(users_file)
    jared = next(u for u in users if u.user_id == "jared")
    assert jared.email == "jared@gmail.com"
    assert jared.broadcast_name == "Jared (SMS)"
    assert jared.ntfy_topic == "jared-topic"
    assert jared.routes == ["inbox", "sos", "ntfy"]
    assert jared.key_file == tmp_path / "jared.key"


def test_load_users_null_fields(users_file):
    users = load_users(users_file)
    family = next(u for u in users if u.user_id == "family")
    assert family.email is None
    assert family.ntfy_topic is None
    assert family.routes == ["sos"]


def test_load_users_key_file_is_path(users_file):
    users = load_users(users_file)
    for user in users:
        assert isinstance(user.key_file, Path)


def test_load_users_expanduser(tmp_path):
    f = tmp_path / "users.json"
    f.write_text(json.dumps({
        "jared": {
            "key_file": "~/.keys/jared.key",
            "email": None,
            "broadcast_name": None,
            "ntfy_topic": None,
            "routes": [],
        }
    }))
    users = load_users(f)
    assert not str(users[0].key_file).startswith("~")


def test_load_users_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        load_users(Path("/nonexistent/users.json"))
