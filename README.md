# mydirs
Command-line tool to bookmark directories and jump to them quickly.

## Features
- Save a directory under a short alias.
- Jump to saved directories from any shell.
- List, find, update, and remove saved entries.
- Track history and basic usage stats.
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
export MYDIRS_DIRECTORY="/absolute/path/to/mydirs"
source "$MYDIRS_DIRECTORY/src/bashrc.sh"
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
- `MYDIRS_DIRECTORY`: Path to this repository.
- `MYDIRS_DB` (optional): Directory where data files are stored. Defaults to `../db/` relative to `MYDIRS_DIRECTORY`.
  - Data files include:
    - `mydirs.sqlite` (saved paths)
    - `mydirs.history` (jump history)
    - `mydirs_stats.json` (usage stats)

Example:

```bash
export MYDIRS_DB="$HOME/.local/share/mydirs/"
```

## Usage

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

### Clean entries that no longer exist
```bash
mydirs -c
# or
mydirs --clean
```

### Show usage stats
```bash
mydirs --stats
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
