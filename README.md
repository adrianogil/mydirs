# mydirs
Command-line tool to bookmark directories and jump to them quickly.

## Features
- Save a directory under a short alias.
- Jump to saved directories from any shell.
- List, find, update, and remove saved entries.
- Rank aliases using frequency and recency.
- Diagnose missing, inaccessible, moved, and duplicate saved directories.
- Track history and usage stats safely across concurrent shells.
- Optional bash helpers and autocompletion.

## Requirements
- Bash (or compatible shell)
- Python 3
- SQLite (bundled with Python)

## Installation

### Option 1: Manual setup (recommended)
1. Clone this repository.
2. Add the following to your shell profile (`~/.bashrc`, `~/.zshrc`, or similar):

```bash
export MYDIRS_DIRECTORY="/absolute/path/to/mydirs/src"
source "$MYDIRS_DIRECTORY/bashrc.sh"
```

This:
- Sets up `PYTHONPATH` to include the package.
- Adds the `mydirs` alias.
- Enables bash autocompletion.
- Installs optional helper functions (`my`, `myd`, `mk`, `m`).

### Option 2: Use the install script
Run the installer to append configuration to `~/.profile`:

```bash
./install.sh
```

### Option 3: Use `gil-install`
If you use `gil-install`, you can run:

```bash
gil-install -i
```

See: https://github.com/adrianogil/gil-tools/blob/master/src/python/gil_install.py

## Configuration
- `MYDIRS_DIRECTORY`: Path to this repository's `src` directory.
- `MYDIRS_DB` (optional): Directory where data files are stored. Defaults to `../db/` relative to `MYDIRS_DIRECTORY`.
  - Data files include:
    - `mydirs.sqlite` (saved paths)
    - `mydirs.history` (jump history)
    - `mydirs_stats.json` (legacy usage stats, imported once when present)

Example:

```bash
export MYDIRS_DB="$HOME/.local/share/mydirs/"
```

Aliases are case-sensitive. Exact alias commands treat characters such as `%`
and `_` literally rather than as database wildcard characters.

The SQLite schema is versioned and upgraded automatically. Existing aliases
remain valid. On the first upgrade, valid counts in the legacy
`mydirs_stats.json` file are imported without modifying or deleting that file.
Usage counts and last-used timestamps are then maintained in SQLite with atomic
updates, so simultaneous shells cannot lose increments. History updates use a
portable sidecar lock and atomic replacement on macOS, Linux, and Termux.

## Usage

### Show help
```bash
mydirs -h
# or
mydirs --help
```

### Save the current directory
```bash
mydirs -s <alias>
# or
mydirs --save <alias>
```

If `<alias>` is omitted, the current folder name is used.

### Open a saved directory
```bash
mydirs -o <alias>
# or
mydirs --open <alias>
```

### Remove a saved alias
```bash
mydirs -r <alias>
# or
mydirs --remove <alias>
```

### Update a saved alias to the current directory
```bash
mydirs -u <alias>
# or
mydirs --update <alias>
```

### List saved directories
```bash
mydirs -l
# or
mydirs --list
```

`--list` retains its alphabetical, `alias:path` output for compatibility.

### Rank saved directories by frecency
```bash
mydirs --rank
```

Normal `--open` navigation increments the alias's use count and records its
last-used time. Ranking uses this deterministic integer formula:

```text
age_days = 30 if last_used is unknown else max(0, (now - last_used) // 86400)
score = use_count * 30000 // (age_days + 30)
```

New aliases with no uses have score zero. Imported legacy counts have no
timestamp, so they start with a conservative 30-day age. Ties are resolved by
most recent use, then higher use count, then the alias's case-sensitive UTF-8
byte order, then its database ID. Autocomplete and the optional fuzzy-picker
helpers use the same ranking. A future last-used timestamp is treated as zero
days old.

### Find saved directories by partial alias
```bash
mydirs -f <search>
# or
mydirs --find <search>
```

### Print a saved path
```bash
mydirs -p <alias>
# or
mydirs --path <alias>
```

### Check whether the current directory is saved
```bash
mydirs -q
# or
mydirs --current
```

### History and back navigation
```bash
mydirs -bh <number>   # Show last N entries
mydirs -bk            # Go back to previous directory
# long options
mydirs --history <number>
mydirs --back
```

### Export and import history backups
Export the directory history to a portable, versioned JSON file:

```bash
mydirs --export-history mydirs-history.json
```

Restore the history from a backup:

```bash
mydirs --import-history mydirs-history.json
```

Import validates the complete backup before replacing the current history. It
rejects malformed or unsupported JSON without changing the existing history,
and collapses consecutive duplicate paths just like normal history tracking.

### Clean entries that no longer exist
```bash
mydirs -c
# or
mydirs --clean
```

`--clean` is the legacy mutating cleanup command. For a safe inspection first,
use the doctor.

### Diagnose stale paths
```bash
mydirs --doctor
```

Doctor is read-only. It reports:

- `MISSING`: the saved path no longer exists, including dangling symlinks.
- `INACCESSIBLE`: the path cannot be inspected, read, or entered.
- `DUPLICATE`: another alias resolves to the same directory, including a
  symlink and its target.
- `MOVED`: the saved filesystem device/inode identity was found at a plausible
  nearby path.
- `NOT-DIRECTORY`: the saved path now names another kind of filesystem entry.

Moved suggestions are conservative: candidates come only from other saved
paths, navigation history, and the missing path's immediate parent, and must
match the device/inode identity captured when the alias was saved or updated.
Doctor never changes a record. To accept a suggestion explicitly:

```bash
mydirs --repair-moved <alias> <new-path>
```

Repair succeeds only when the new path is an accessible directory with the
same stored filesystem identity. It preserves the alias's usage history. For a
deliberate unrelated replacement, change to the new directory and continue to
use the backward-compatible `mydirs --update <alias>` command.

### Show usage stats
```bash
mydirs --stats
```

Stats retain the historical `path: count` display and are now derived from the
transactional SQLite usage records.

### Show database path
```bash
mydirs --db
```

## Examples
```bash
# Save current directory as "work"
mydirs -s work

# Jump to it
mydirs -o work

# Update alias to the current directory
mydirs -u work

# List all entries
mydirs -l
```

## Helper functions (from `src/bashrc.sh`)
These are optional but useful if you source `src/bashrc.sh`.

- `my` saves the current directory or opens an alias.
  - `my` (save current directory)
  - `my <alias>` (open alias)
- `myd` opens a fuzzy picker for commands (requires `default-fuzzy-finder`).
- `mk` opens a fuzzy picker for aliases.
- `m` opens a tmux session named after the alias (requires `tmux` and `tenter`/`tnew`).

## Uninstall
1. Remove `mydirs` entries from your shell profile (`~/.bashrc`, `~/.zshrc`, or `~/.profile`).
2. Remove the data directory (`$MYDIRS_DB`) if you want to delete saved paths.

## Contributing
PRs are welcome. Please keep changes focused and add documentation for new behavior.

## Development status
This project is in an early/alpha state and may not follow consistent coding standards.

## See also
- https://github.com/huyng/bashmarks
