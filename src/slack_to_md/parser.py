from __future__ import annotations

import json
import re
import zipfile
from pathlib import PurePosixPath

from .models import Attachment, Channel, File, Message, User


def load_users(zf: zipfile.ZipFile) -> dict[str, User]:
    """Load users.json and return a dict mapping user ID to User."""
    users: dict[str, User] = {}
    for name in zf.namelist():
        if PurePosixPath(name).name == "users.json":
            data = json.loads(zf.read(name))
            for u in data:
                profile = u.get("profile", {})
                users[u["id"]] = User(
                    id=u["id"],
                    name=u.get("name", ""),
                    display_name=profile.get("display_name", ""),
                    real_name=u.get("real_name", ""),
                )
            break
    return users


def load_channels(zf: zipfile.ZipFile) -> list[Channel]:
    """Load channels.json and return a list of Channel objects."""
    channels: list[Channel] = []
    for name in zf.namelist():
        if PurePosixPath(name).name == "channels.json":
            data = json.loads(zf.read(name))
            for c in data:
                topic = c.get("topic", {}).get("value", "")
                purpose = c.get("purpose", {}).get("value", "")
                channels.append(
                    Channel(
                        id=c["id"],
                        name=c["name"],
                        topic=topic,
                        purpose=purpose,
                    )
                )
            break
    return channels


def _parse_message(raw: dict) -> Message:
    """Parse a raw message dict into a Message object."""
    attachments = [
        Attachment(
            title=a.get("title", ""),
            fallback=a.get("fallback", ""),
            text=a.get("text", ""),
            from_url=a.get("from_url", ""),
        )
        for a in raw.get("attachments", [])
    ]
    files = [
        File(
            name=f.get("name", ""),
            url_private=f.get("url_private", ""),
            permalink=f.get("permalink", ""),
        )
        for f in raw.get("files", [])
    ]
    return Message(
        user=raw.get("user", ""),
        text=raw.get("text", ""),
        ts=raw.get("ts", ""),
        thread_ts=raw.get("thread_ts", ""),
        attachments=attachments,
        files=files,
        subtype=raw.get("subtype", ""),
    )


def load_channel_messages(
    zf: zipfile.ZipFile, channel_name: str, users: dict[str, User]
) -> list[Message]:
    """Load all messages for a channel, sorted by timestamp, with threads assembled.

    Also backfills the users dict with user_profile data from messages
    (for external/Slack Connect users not in users.json).
    """
    date_pattern = re.compile(
        rf"^(?:.+/)?{re.escape(channel_name)}/(\d{{4}}-\d{{2}}-\d{{2}})\.json$"
    )

    # Collect all date JSON files for this channel
    date_files: list[tuple[str, str]] = []
    for name in zf.namelist():
        m = date_pattern.match(name)
        if m:
            date_files.append((m.group(1), name))

    date_files.sort(key=lambda x: x[0])

    # Parse all messages and backfill users from inline profiles
    all_messages: list[Message] = []
    for _, filepath in date_files:
        data = json.loads(zf.read(filepath))
        for raw in data:
            all_messages.append(_parse_message(raw))
            # Backfill users dict from user_profile embedded in messages
            uid = raw.get("user", "")
            if uid and uid not in users:
                profile = raw.get("user_profile", {})
                if profile:
                    users[uid] = User(
                        id=uid,
                        name=profile.get("name", ""),
                        display_name=profile.get("display_name", ""),
                        real_name=profile.get("real_name", ""),
                    )

    # Sort by timestamp
    all_messages.sort(key=lambda m: float(m.ts) if m.ts else 0.0)

    # Assemble threads: group replies under their parent
    top_level: list[Message] = []
    parents: dict[str, Message] = {}

    for msg in all_messages:
        is_reply = msg.thread_ts and msg.thread_ts != msg.ts
        if not is_reply:
            top_level.append(msg)
            parents[msg.ts] = msg
        else:
            parent = parents.get(msg.thread_ts)
            if parent:
                parent.replies.append(msg)
            else:
                # Orphan reply — treat as top-level
                top_level.append(msg)

    return top_level
