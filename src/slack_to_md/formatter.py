from __future__ import annotations

import re
from datetime import datetime, timezone

from .models import Channel, Message, User


def _format_timestamp(ts: str) -> str:
    """Convert a Slack timestamp to a human-readable time string."""
    try:
        dt = datetime.fromtimestamp(float(ts), tz=timezone.utc)
        return dt.strftime("%I:%M %p").lstrip("0")
    except ValueError, OSError:
        return ts


def _format_date(ts: str) -> str:
    """Convert a Slack timestamp to a YYYY-MM-DD date string."""
    try:
        dt = datetime.fromtimestamp(float(ts), tz=timezone.utc)
        return dt.strftime("%Y-%m-%d")
    except ValueError, OSError:
        return ""


def convert_mrkdwn(text: str, users: dict[str, User]) -> str:
    """Convert Slack mrkdwn to standard Markdown."""

    # User mentions: <@U12345> or <@U12345|name>
    def replace_user_mention(m: re.Match) -> str:
        uid = m.group(1)
        user = users.get(uid)
        label = user.label if user else uid
        return f"**@{label}**"

    text = re.sub(r"<@(\w+)(?:\|[^>]*)?>", replace_user_mention, text)

    # Channel mentions: <#C12345|channel-name>
    text = re.sub(r"<#\w+\|([^>]+)>", r"#\1", text)

    # User group mentions: <!subteam^S12345|@group>
    text = re.sub(r"<!subteam\^\w+\|(@[^>]+)>", r"\1", text)

    # Special mentions
    text = re.sub(r"<!here(?:\|[^>]*)?>", "@here", text)
    text = re.sub(r"<!channel(?:\|[^>]*)?>", "@channel", text)
    text = re.sub(r"<!everyone(?:\|[^>]*)?>", "@everyone", text)

    # Links: <url|label> → [label](url), <url> → url
    def replace_link(m: re.Match) -> str:
        content = m.group(1)
        if "|" in content:
            url, label = content.split("|", 1)
            return f"[{label}]({url})"
        return content

    text = re.sub(r"<(https?://[^>]+)>", replace_link, text)

    # Slack bold *text* → Markdown bold **text** (but not inside code)
    # Only match single * not preceded/followed by another *
    text = _convert_slack_formatting(text)

    return text


def _convert_slack_formatting(text: str) -> str:
    """Convert Slack formatting (*bold*, _italic_, ~strike~) to Markdown equivalents.

    Preserves content inside code spans and code blocks.
    """
    parts: list[str] = []
    i = 0
    n = len(text)
    buf_start = 0  # start of current non-code segment

    while i < n:
        # Code block: ```...```
        if text[i : i + 3] == "```":
            if i > buf_start:
                parts.append(text[buf_start:i])
            end = text.find("```", i + 3)
            if end != -1:
                parts.append(text[i : end + 3])
                i = end + 3
            else:
                parts.append(text[i:])
                i = n
            buf_start = i
            continue
        # Inline code: `...`
        if text[i] == "`":
            end = text.find("`", i + 1)
            if end != -1:
                if i > buf_start:
                    parts.append(text[buf_start:i])
                parts.append(text[i : end + 1])
                i = end + 1
                buf_start = i
                continue

        i += 1

    if buf_start < n:
        parts.append(text[buf_start:])

    result: list[str] = []
    for part in parts:
        if part.startswith("`"):
            result.append(part)
        else:
            # Slack *bold* → **bold**
            part = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"**\1**", part)
            # Slack _italic_ → *italic*
            part = re.sub(r"(?<![_\w])_(?!_)(.+?)(?<!_)_(?![_\w])", r"*\1*", part)
            # Slack ~strike~ → ~~strike~~
            part = re.sub(r"(?<!~)~(?!~)(.+?)(?<!~)~(?!~)", r"~~\1~~", part)
            result.append(part)

    return "".join(result)


def format_message(msg: Message, users: dict[str, User], indent: bool = False) -> str:
    """Format a single message as Markdown."""
    user = users.get(msg.user)
    author = user.label if user else msg.user or "unknown"
    time_str = _format_timestamp(msg.ts)
    text = convert_mrkdwn(msg.text, users)

    prefix = "  " if indent else ""
    thread_label = " [thread]" if indent else ""

    lines: list[str] = []
    lines.append(f"{prefix}**@{author}** ({time_str}){thread_label}:")
    if text:
        for line in text.split("\n"):
            lines.append(f"{prefix}{line}")

    # Render attachments
    for att in msg.attachments:
        if att.from_url:
            label = att.title or att.fallback or "Link"
            lines.append(f"{prefix}[{label}]({att.from_url})")
        elif att.title or att.fallback:
            lines.append(f"{prefix}[Attachment: {att.title or att.fallback}]")

    # Render files
    for f in msg.files:
        url = f.permalink or f.url_private
        if url:
            lines.append(f"{prefix}[{f.name or 'File'}]({url})")
        else:
            lines.append(f"{prefix}[Attachment: {f.name or 'File'}]")

    return "\n".join(lines)


def format_channel(
    channel: Channel,
    messages: list[Message],
    users: dict[str, User],
) -> str:
    """Format an entire channel as a Markdown document."""
    lines: list[str] = []
    lines.append(f"# #{channel.name}")
    lines.append("")

    if channel.topic:
        lines.append(f"**Topic:** {channel.topic}")
    if channel.purpose:
        lines.append(f"**Purpose:** {channel.purpose}")
    if channel.topic or channel.purpose:
        lines.append("")

    current_date = ""
    for msg in messages:
        # Skip join/leave subtypes
        if msg.subtype in (
            "channel_join",
            "channel_leave",
            "channel_purpose",
            "channel_topic",
            "channel_name",
            "bot_message",
        ):
            continue

        msg_date = _format_date(msg.ts)
        if msg_date and msg_date != current_date:
            if current_date:
                lines.append("")
            lines.append("---")
            lines.append("")
            lines.append(f"## {msg_date}")
            lines.append("")
            current_date = msg_date

        lines.append(format_message(msg, users))
        lines.append("")

        # Render thread replies
        for reply in msg.replies:
            lines.append(format_message(reply, users, indent=True))
            lines.append("")

    return "\n".join(lines)
