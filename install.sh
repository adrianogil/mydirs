#!/usr/bin/env bash
set -e

project_directory=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
mydirs_directory="$project_directory/src"
profile_file="${MYDIRS_PROFILE:-$HOME/.profile}"
marker='# MyDirs managed setup'

touch "$profile_file"
if grep -F "$marker" "$profile_file" >/dev/null 2>&1; then
    printf 'MyDirs is already configured in %s\n' "$profile_file"
    exit 0
fi

{
    printf '\n%s\n' "$marker"
    printf 'export MYDIRS_DIRECTORY=%q\n' "$mydirs_directory"
    printf 'source "$MYDIRS_DIRECTORY/bashrc.sh"\n'
} >> "$profile_file"

printf 'MyDirs configuration added to %s\n' "$profile_file"
printf 'Reload your shell profile or start a new shell to use mydirs.\n'
