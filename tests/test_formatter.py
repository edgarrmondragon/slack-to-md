from __future__ import annotations

from slack_to_md.formatter import (
    _convert_slack_formatting,
    _format_date,
    _format_timestamp,
    convert_mrkdwn,
    format_channel,
    format_message,
)
from slack_to_md.models import Attachment, Channel, File, Message, User

USERS = {
    "U001": User(
        id="U001", name="alice", display_name="alice", real_name="Alice Smith"
    ),
    "U002": User(id="U002", name="bob", display_name="", real_name="Bob Jones"),
}


class TestFormatTimestamp:
    def test_valid_timestamp(self):
        # 2024-01-15 08:30:00 UTC
        assert _format_timestamp("1705307400.000100") == "8:30 AM"

    def test_noon(self):
        # 2024-01-15 12:00:00 UTC = epoch 1705320000
        assert _format_timestamp("1705320000.000000") == "12:00 PM"

    def test_invalid_timestamp(self):
        assert _format_timestamp("not-a-number") == "not-a-number"


class TestFormatDate:
    def test_valid_timestamp(self):
        assert _format_date("1705307400.000100") == "2024-01-15"

    def test_invalid_timestamp(self):
        assert _format_date("bad") == ""


class TestConvertMrkdwn:
    def test_user_mention_known(self):
        assert convert_mrkdwn("Hello <@U001>!", USERS) == "Hello **@alice**!"

    def test_user_mention_unknown(self):
        assert convert_mrkdwn("Hello <@U999>!", USERS) == "Hello **@U999**!"

    def test_user_mention_with_label(self):
        assert convert_mrkdwn("<@U001|alice>", USERS) == "**@alice**"

    def test_channel_mention(self):
        assert convert_mrkdwn("<#C123|general>", USERS) == "#general"

    def test_subteam_mention(self):
        assert convert_mrkdwn("<!subteam^S123|@engineers>", USERS) == "@engineers"

    def test_here_mention(self):
        assert convert_mrkdwn("<!here>", USERS) == "@here"

    def test_channel_broadcast(self):
        assert convert_mrkdwn("<!channel>", USERS) == "@channel"

    def test_everyone_mention(self):
        assert convert_mrkdwn("<!everyone>", USERS) == "@everyone"

    def test_link_with_label(self):
        result = convert_mrkdwn("<https://example.com|Example>", USERS)
        assert result == "[Example](https://example.com)"

    def test_link_without_label(self):
        result = convert_mrkdwn("<https://example.com>", USERS)
        assert result == "https://example.com"

    def test_bold(self):
        assert convert_mrkdwn("this is *bold* text", USERS) == "this is **bold** text"

    def test_italic(self):
        assert convert_mrkdwn("this is _italic_ text", USERS) == "this is *italic* text"

    def test_strikethrough(self):
        assert (
            convert_mrkdwn("this is ~struck~ text", USERS) == "this is ~~struck~~ text"
        )

    def test_combined_formatting(self):
        result = convert_mrkdwn("*bold* and _italic_ and ~strike~", USERS)
        assert result == "**bold** and *italic* and ~~strike~~"

    def test_multiple_mentions_in_one_message(self):
        result = convert_mrkdwn("cc <@U001> and <@U002>", USERS)
        assert result == "cc **@alice** and **@Bob Jones**"


class TestConvertSlackFormatting:
    def test_preserves_inline_code(self):
        result = _convert_slack_formatting("use `*not bold*` here")
        assert result == "use `*not bold*` here"

    def test_preserves_code_block(self):
        result = _convert_slack_formatting("```*not bold*```")
        assert result == "```*not bold*```"

    def test_bold_outside_code(self):
        result = _convert_slack_formatting("*bold* and `code`")
        assert result == "**bold** and `code`"

    def test_no_formatting(self):
        assert _convert_slack_formatting("plain text") == "plain text"

    def test_unclosed_code_block(self):
        result = _convert_slack_formatting("```unclosed")
        assert result == "```unclosed"


class TestFormatMessage:
    def test_basic_message(self):
        msg = Message(user="U001", text="hello", ts="1705307400.000100")
        result = format_message(msg, USERS)
        assert "**@alice**" in result
        assert "hello" in result

    def test_unknown_user(self):
        msg = Message(user="U999", text="hi", ts="1705307400.000100")
        result = format_message(msg, USERS)
        assert "**@U999**" in result

    def test_empty_user(self):
        msg = Message(user="", text="hi", ts="1705307400.000100")
        result = format_message(msg, USERS)
        assert "**@unknown**" in result

    def test_indented_thread_reply(self):
        msg = Message(user="U001", text="reply", ts="1705307400.000100")
        result = format_message(msg, USERS, indent=True)
        assert result.startswith("  ")
        assert "[thread]" in result

    def test_attachment_with_url(self):
        att = Attachment(title="PR #1", from_url="https://github.com/pr/1")
        msg = Message(user="U001", text="", ts="1705307400.000100", attachments=[att])
        result = format_message(msg, USERS)
        assert "[PR #1](https://github.com/pr/1)" in result

    def test_attachment_without_url(self):
        att = Attachment(title="Some doc")
        msg = Message(user="U001", text="", ts="1705307400.000100", attachments=[att])
        result = format_message(msg, USERS)
        assert "[Attachment: Some doc]" in result

    def test_file_with_permalink(self):
        f = File(name="image.png", permalink="https://files.slack.com/image.png")
        msg = Message(user="U001", text="", ts="1705307400.000100", files=[f])
        result = format_message(msg, USERS)
        assert "[image.png](https://files.slack.com/image.png)" in result

    def test_file_without_url(self):
        f = File(name="secret.pdf")
        msg = Message(user="U001", text="", ts="1705307400.000100", files=[f])
        result = format_message(msg, USERS)
        assert "[Attachment: secret.pdf]" in result


class TestFormatChannel:
    def test_header_with_topic_and_purpose(self):
        channel = Channel(id="C1", name="general", topic="Fun stuff", purpose="Be nice")
        result = format_channel(channel, [], USERS)
        assert "# #general" in result
        assert "**Topic:** Fun stuff" in result
        assert "**Purpose:** Be nice" in result

    def test_header_no_topic(self):
        channel = Channel(id="C1", name="random")
        result = format_channel(channel, [], USERS)
        assert "# #random" in result
        assert "Topic" not in result

    def test_skips_system_subtypes(self):
        channel = Channel(id="C1", name="test")
        messages = [
            Message(
                user="U001",
                text="joined",
                ts="1705307400.000100",
                subtype="channel_join",
            ),
            Message(user="U001", text="real message", ts="1705307401.000100"),
        ]
        result = format_channel(channel, messages, USERS)
        assert "joined" not in result
        assert "real message" in result

    def test_date_headers(self):
        channel = Channel(id="C1", name="test")
        messages = [
            Message(user="U001", text="day one", ts="1705307400.000100"),  # 2024-01-15
            Message(user="U001", text="day two", ts="1705393800.000100"),  # 2024-01-16
        ]
        result = format_channel(channel, messages, USERS)
        assert "## 2024-01-15" in result
        assert "## 2024-01-16" in result

    def test_thread_replies_rendered(self):
        channel = Channel(id="C1", name="test")
        reply = Message(user="U002", text="thread reply", ts="1705307500.000100")
        parent = Message(
            user="U001", text="parent", ts="1705307400.000100", replies=[reply]
        )
        result = format_channel(channel, [parent], USERS)
        assert "parent" in result
        assert "thread reply" in result
        assert "[thread]" in result
