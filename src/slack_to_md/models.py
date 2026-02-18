from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class User:
    id: str
    name: str
    display_name: str = ""
    real_name: str = ""

    @property
    def label(self) -> str:
        return self.display_name or self.real_name or self.name


@dataclass
class Attachment:
    title: str = ""
    fallback: str = ""
    text: str = ""
    from_url: str = ""


@dataclass
class File:
    name: str = ""
    url_private: str = ""
    permalink: str = ""


@dataclass
class Message:
    user: str
    text: str
    ts: str
    thread_ts: str = ""
    replies: list[Message] = field(default_factory=list)
    attachments: list[Attachment] = field(default_factory=list)
    files: list[File] = field(default_factory=list)
    subtype: str = ""


@dataclass
class Channel:
    id: str
    name: str
    topic: str = ""
    purpose: str = ""
