from __future__ import annotations

import io
import json
import zipfile

from slack_to_md.models import User
from slack_to_md.parser import load_channel_messages, load_channels, load_users


def _make_zip(files: dict[str, object]) -> zipfile.ZipFile:
    """Create an in-memory ZIP file from a dict of {path: data}."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for path, data in files.items():
            zf.writestr(path, json.dumps(data))
    buf.seek(0)
    return zipfile.ZipFile(buf, "r")


class TestLoadUsers:
    def test_loads_users(self):
        zf = _make_zip(
            {
                "users.json": [
                    {
                        "id": "U001",
                        "name": "alice",
                        "real_name": "Alice Smith",
                        "profile": {"display_name": "alice"},
                    },
                    {
                        "id": "U002",
                        "name": "bob",
                        "real_name": "Bob",
                        "profile": {},
                    },
                ]
            }
        )
        users = load_users(zf)
        assert len(users) == 2
        assert users["U001"].display_name == "alice"
        assert users["U002"].real_name == "Bob"

    def test_empty_export(self):
        zf = _make_zip({"users.json": []})
        assert load_users(zf) == {}

    def test_missing_users_json(self):
        zf = _make_zip({"channels.json": []})
        assert load_users(zf) == {}


class TestLoadChannels:
    def test_loads_channels(self):
        zf = _make_zip(
            {
                "channels.json": [
                    {
                        "id": "C001",
                        "name": "general",
                        "topic": {"value": "General"},
                        "purpose": {"value": "Main channel"},
                    },
                ]
            }
        )
        channels = load_channels(zf)
        assert len(channels) == 1
        assert channels[0].name == "general"
        assert channels[0].topic == "General"
        assert channels[0].purpose == "Main channel"

    def test_missing_topic_purpose(self):
        zf = _make_zip({"channels.json": [{"id": "C001", "name": "bare"}]})
        channels = load_channels(zf)
        assert channels[0].topic == ""
        assert channels[0].purpose == ""


class TestLoadChannelMessages:
    def test_loads_and_sorts_messages(self):
        zf = _make_zip(
            {
                "users.json": [],
                "general/2024-01-15.json": [
                    {"user": "U001", "text": "second", "ts": "1705307500.000"},
                    {"user": "U001", "text": "first", "ts": "1705307400.000"},
                ],
            }
        )
        users: dict[str, User] = {}
        messages = load_channel_messages(zf, "general", users)
        assert len(messages) == 2
        assert messages[0].text == "first"
        assert messages[1].text == "second"

    def test_assembles_threads(self):
        parent_ts = "1705307400.000"
        zf = _make_zip(
            {
                "general/2024-01-15.json": [
                    {
                        "user": "U001",
                        "text": "parent",
                        "ts": parent_ts,
                        "thread_ts": parent_ts,
                    },
                    {
                        "user": "U002",
                        "text": "reply",
                        "ts": "1705307500.000",
                        "thread_ts": parent_ts,
                    },
                ],
            }
        )
        users: dict[str, User] = {}
        messages = load_channel_messages(zf, "general", users)
        assert len(messages) == 1
        assert messages[0].text == "parent"
        assert len(messages[0].replies) == 1
        assert messages[0].replies[0].text == "reply"

    def test_orphan_reply_becomes_top_level(self):
        zf = _make_zip(
            {
                "general/2024-01-15.json": [
                    {
                        "user": "U001",
                        "text": "orphan",
                        "ts": "1705307500.000",
                        "thread_ts": "9999.000",
                    },
                ],
            }
        )
        users: dict[str, User] = {}
        messages = load_channel_messages(zf, "general", users)
        assert len(messages) == 1
        assert messages[0].text == "orphan"

    def test_backfills_users_from_profile(self):
        zf = _make_zip(
            {
                "general/2024-01-15.json": [
                    {
                        "user": "U999",
                        "text": "hello",
                        "ts": "1705307400.000",
                        "user_profile": {
                            "name": "ext_user",
                            "display_name": "External User",
                            "real_name": "Ext U.",
                        },
                    },
                ],
            }
        )
        users: dict[str, User] = {}
        load_channel_messages(zf, "general", users)
        assert "U999" in users
        assert users["U999"].display_name == "External User"

    def test_does_not_overwrite_existing_user(self):
        zf = _make_zip(
            {
                "general/2024-01-15.json": [
                    {
                        "user": "U001",
                        "text": "hi",
                        "ts": "1705307400.000",
                        "user_profile": {
                            "name": "wrong",
                            "display_name": "Wrong Name",
                            "real_name": "Wrong",
                        },
                    },
                ],
            }
        )
        users = {"U001": User(id="U001", name="alice", display_name="alice")}
        load_channel_messages(zf, "general", users)
        assert users["U001"].display_name == "alice"

    def test_multiple_date_files_sorted(self):
        zf = _make_zip(
            {
                "general/2024-01-16.json": [
                    {"user": "U001", "text": "day two", "ts": "1705393800.000"},
                ],
                "general/2024-01-15.json": [
                    {"user": "U001", "text": "day one", "ts": "1705307400.000"},
                ],
            }
        )
        users: dict[str, User] = {}
        messages = load_channel_messages(zf, "general", users)
        assert messages[0].text == "day one"
        assert messages[1].text == "day two"


class TestModels:
    def test_user_label_prefers_display_name(self):
        user = User(id="U1", name="login", display_name="Display", real_name="Real")
        assert user.label == "Display"

    def test_user_label_falls_back_to_real_name(self):
        user = User(id="U1", name="login", real_name="Real")
        assert user.label == "Real"

    def test_user_label_falls_back_to_name(self):
        user = User(id="U1", name="login")
        assert user.label == "login"
