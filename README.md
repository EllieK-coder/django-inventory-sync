# Minecraft Server Backup

A Python command-line tool that creates safe, consistent backups of a Minecraft server world and automatically rotates old archives so disk usage stays under control.

Built for modded (Forge) servers, where worlds get large and a corrupted save can mean losing weeks of progress.

## Why

Copying a world folder while the server is running can produce a broken backup, because the game may be writing chunks to disk at the same time. This tool talks to the server over **RCON** to pause autosaving and flush everything to disk first. Then it archives the world and turns saving back on.

## Features

- **Consistent snapshots**: uses RCON (`save-off` → `save-all` → `save-on`) so the world isn't being written to mid-backup
- **Compressed, timestamped archives** of the world folder
- **Backup rotation**: keeps the N most recent backups and deletes older ones automatically
- **Installable CLI**: one `mcbackup` command, packaged with a `pyproject.toml` entry point
- **Tested** with `pytest`

<!-- TODO: remove or adjust any feature above that isn't implemented yet -->

## Requirements

- Python 3.11+
- A Minecraft server with RCON enabled (`enable-rcon=true` in `server.properties`)

## Installation

```bash
git clone https://github.com/EllieK-coder/mcbackup.git
cd mcbackup
pip install -e .
```

## Usage

```bash
# TODO: replace with the real arguments once the CLI is finished
mcbackup --world "C:/servers/GrandVampirismo/world" --dest "D:/backups" --keep 7
```

| Option    | Description                          |
|-----------|--------------------------------------|
| `--world` | Path to the server's world folder    |
| `--dest`  | Folder where archives are stored     |
| `--keep`  | Number of recent backups to keep     |

### Scheduling

To run backups automatically, schedule `mcbackup` with **Task Scheduler** (Windows) or **cron** (Linux).

## Project structure

```
src/mcbackup/   # package source (CLI entry point: mcbackup.cli:main)
tests/          # pytest test suite
pyproject.toml  # packaging and dependencies (hatchling)
```

## Running tests

```bash
pip install pytest
pytest
```

## Roadmap

- [x] Project skeleton and CLI entry point
- [x] Archive the world folder
- [ ] RCON save-off / save-all / save-on around the backup
- [ ] Rotation of old backups
- [ ] Config file support
- [ ] Logging

## Tech stack

Python · RCON (`mcrcon`) · pytest · hatchling
