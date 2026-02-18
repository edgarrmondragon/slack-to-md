# slack-to-md

[![CI](https://github.com/edgarrmondragon/slack-to-md/actions/workflows/ci.yml/badge.svg)](https://github.com/edgarrmondragon/slack-to-md/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/github/license/edgarrmondragon/slack-to-md)](https://github.com/edgarrmondragon/slack-to-md/blob/main/LICENSE)
[![Python: 3.14+](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2Fedgarrmondragon%2Fslack-to-md%2Fmain%2Fpyproject.toml)](https://github.com/edgarrmondragon/slack-to-md)

Convert a Slack workspace export ZIP into Markdown files.

## Installation

```bash
uv tool install slack-to-md
```

## Usage

```bash
# Export all channels
slack-to-md -z export.zip

# Export specific channels
slack-to-md -z export.zip -c general -c random

# Export to a specific directory
slack-to-md -z export.zip -c announcements -o output/
```

## Options

| Flag | Description |
|---|---|
| `-z`, `--zip` | Path to Slack export ZIP file (required) |
| `-c`, `--channel` | Channel name to export (repeatable, defaults to all) |
| `-o`, `--output-dir` | Output directory (default: current dir) |
