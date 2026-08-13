# Add the following lines to your bashrc:
# export MYDIRS_DIRECTORY=<path-to>/GitRepoWatcher
# source $MYDIRS_DIRECTORY/src/bashrc.sh

if [[ -z "$MYDIRS_PYTHON_PATH" ]];
then
    export MYDIRS_PYTHON_PATH="$MYDIRS_DIRECTORY/python/"
    export PYTHONPATH="$MYDIRS_PYTHON_PATH${PYTHONPATH:+:$PYTHONPATH}"
fi

alias mydirs='. "$MYDIRS_DIRECTORY/mydirs.sh"'
if [ -x "$BASH" ] && shopt -q >/dev/null 2>&1; then
   source "$MYDIRS_DIRECTORY/autocompletion_mydirs.sh"
fi


function my()
{
    if [ -z "$1" ]; then
        mydirs -s
    else
        mydirs -o "$1"
    fi
}

function mydirs-rnd()
{
    local shuffle_command target_alias
    if command -v shuf >/dev/null 2>&1; then
        shuffle_command=shuf
    elif command -v gshuf >/dev/null 2>&1; then
        shuffle_command=gshuf
    else
        echo "mydirs: shuf or gshuf is required" >&2
        return 1
    fi
    target_alias=$(mydirs --auto-list | "$shuffle_command" -n1)
    mydirs -o "$target_alias"
}

function mydirs-path-pick()
{
    local target_alias target_path
    target_alias=$(mydirs --auto-list | default-fuzzy-finder)
    target_path=$(mydirs -p "$target_alias")
    printf '%s\n' "$target_path" | copy-text-to-clipboard
    printf '%s\n' "$target_path"
}

function mytmux()
{
    local dir_alias dir_path
    if [ -z "$1" ]; then
        dir_alias=$(mydirs --auto-list | default-fuzzy-finder)
    else
        dir_alias=$1
    fi

    dir_path=$(mydirs -p "$dir_alias")

    if tmux has-session -t "$dir_alias" 2>/dev/null; then
        # echo "Session exists."
        tenter "$dir_alias"
    else
        # echo "Session does not exist."
        tnew "$dir_alias" "$dir_path"
    fi
}
if [ -x "$BASH" ] && shopt -q >/dev/null 2>&1; then
   complete -F _my mytmux
fi
alias m="mytmux"

function mytmux-detached()
{
    local dir_alias dir_path
    if [ -z "$1" ]; then
        dir_alias=$(mydirs -l | tr ':' '\t' | default-fuzzy-finder | tr '\t' ' ' | awk '{print $1}')
    else
        dir_alias=$1
    fi

    dir_path=$(mydirs -p "$dir_alias")
    tmux new-session -d -s "$dir_alias" -c "$dir_path"
}


function mydirs-default-fuzzy-finder()
{
    local mydirs_option mydirs_args
    mydirs_option=$(mydirs --list-args | tr ' ' '\n' | default-fuzzy-finder)
    echo $mydirs_option

    if [[ "${mydirs_option}" == "--open" || "${mydirs_option}" == "-o" || "${mydirs_option}" == "--remove" || "${mydirs_option}" == "-r" ]] ; then
        mydirs_args=$(mydirs --auto-list | default-fuzzy-finder)

        mydirs "${mydirs_option}" "${mydirs_args}"
    else
        mydirs "${mydirs_option}"
    fi
}
alias myd="mydirs-default-fuzzy-finder"

function mydirs-open-default-fuzzy-finder()
{
    local mydirs_args
    mydirs_args=$(mydirs --auto-list | default-fuzzy-finder)
    mydirs -o "${mydirs_args}"
}
alias mk="mydirs-open-default-fuzzy-finder"
