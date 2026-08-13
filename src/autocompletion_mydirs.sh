_mydirs_alias_completions()
{
    local cur alias_name
    cur="$1"
    while IFS= read -r alias_name; do
        case "$alias_name" in
            "$cur"*) COMPREPLY+=("$alias_name") ;;
        esac
    done < <(python3 -m mydirs --auto-list)
}

_mydirs()
{
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    opts="--save -s --open -o --remove -r --update -u --list -l --find -f --path -p --current -q --history -bh --back -bk --clean -c --rank --doctor --repair-moved --stats --db --export-history --import-history --list-args --auto-list --help -h"

    if [[ "$prev" == "--open" || "$prev" == "-o" ||
          "$prev" == "--remove" || "$prev" == "-r" ||
          "$prev" == "--update" || "$prev" == "-u" ||
          "$prev" == "--path" || "$prev" == "-p" ||
          "$prev" == "--repair-moved" ]]; then
        _mydirs_alias_completions "$cur"
        return 0
    fi

    if [[ "$cur" == -* ]]; then
        COMPREPLY=( $(compgen -W "$opts" -- "$cur") )
    fi
}
complete -F _mydirs mydirs

_my()
{
    COMPREPLY=()
    _mydirs_alias_completions "${COMP_WORDS[COMP_CWORD]}"
}
complete -F _my my
