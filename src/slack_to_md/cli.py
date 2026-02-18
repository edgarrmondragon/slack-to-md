from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

from rich.console import Console

from .formatter import format_channel
from .parser import load_channel_messages, load_channels, load_users

console = Console(stderr=True)


def main() -> None:
    """Convert a Slack workspace export ZIP into Markdown files."""
    parser = argparse.ArgumentParser(
        description="Convert a Slack workspace export ZIP into Markdown files.",
    )
    parser.add_argument(
        "-z",
        "--zip",
        dest="zip_path",
        required=True,
        type=Path,
        help="Path to Slack export ZIP file.",
    )
    parser.add_argument(
        "-c",
        "--channel",
        dest="channels",
        action="append",
        help="Channel name to export (repeatable). Defaults to all channels.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        default=".",
        type=Path,
        help="Output directory for Markdown files (default: current dir).",
    )
    args = parser.parse_args()

    zip_path: Path = args.zip_path
    if not zip_path.exists():
        console.print(f"[red bold]Error:[/] ZIP file not found: {zip_path}")
        raise SystemExit(1)

    with zipfile.ZipFile(zip_path, "r") as zf:
        users = load_users(zf)
        all_channels = load_channels(zf)

        if not all_channels:
            console.print("[red bold]Error:[/] No channels found in export.")
            raise SystemExit(1)

        if args.channels:
            requested = {name.strip() for name in args.channels}
            selected = [c for c in all_channels if c.name in requested]
            missing = requested - {c.name for c in selected}
            if missing:
                console.print(
                    f"[yellow]Warning:[/] channels not found in export: {', '.join(sorted(missing))}"
                )
        else:
            selected = all_channels

        if not selected:
            console.print("[red bold]Error:[/] No matching channels to export.")
            console.print(
                f"Available channels: {', '.join(c.name for c in all_channels)}"
            )
            raise SystemExit(1)

        output_dir: Path = args.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        for channel in selected:
            with console.status(f"Processing [bold]#{channel.name}[/]..."):
                messages = load_channel_messages(zf, channel.name, users)
                markdown = format_channel(channel, messages, users)

                out_file = output_dir / f"{channel.name}.md"
                out_file.write_text(markdown, encoding="utf-8")

            console.print(
                f"  [green]✓[/] [bold]#{channel.name}[/] → {out_file} ({len(messages)} messages)"
            )

    console.print("[green bold]Done.[/]")
