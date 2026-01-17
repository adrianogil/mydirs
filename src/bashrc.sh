# Add the following lines to your bashrc:
# export MYDIRS_DIRECTORY=<path-to>/GitRepoWatcher
# source $MYDIRS_DIRECTORY/src/bashrc.sh

if [[ -z "$MYDIRS_PYTHON_PATH" ]];
then
    export MYDIRS_PYTHON_PATH=$MYDIRS_DIRECTORY/python/
    export PYTHONPATH=$MYDIRS_PYTHON_PATH:$PYTHONPATH
fi

alias mydirs=". "$MYDIRS_DIRECTORY"/mydirs.sh"
if [ -x "$BASH" ] && shopt -q >/dev/null 2>&1; then
   source $MYDIRS_DIRECTORY"/autocompletion_mydirs.sh"
fi


function my()
{
    if [ -z "$1" ]; then
        mydirs -s
    else
        mydirs -o $1
    fi
}

function mydirs-rnd()
{
    if [[ $0 == *termux* ]]; then
        mydirs -o $(mydirs -l | shuf -n1 | sed 's/:/ /g' | awk '{print $1}')
    else
        mydirs -o $(mydirs -l | gshuf -n1 | sed 's/:/ /g' | awk '{print $1}')
    fi
}

function mydirs-path-pick()
{
    target_alias=$(mydirs -l | tr ':' '\t' | default-fuzzy-finder | tr '\t' ' ' | awk '{print $1}')
    target_path=$(mydirs -p $target_alias)
    echo $target_path | copy-text-to-clipboard
    echo $target_path
}

function mytmux()
{
    if [ -z "$1" ]; then
        dir_alias=$(mydirs -l | tr ':' '\t' | default-fuzzy-finder | tr '\t' ' ' | awk '{print $1}')
    else
        dir_alias=$1
    fi

    dir_path=$(mydirs -p $dir_alias)

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
    if [ -z "$1" ]; then
        dir_alias=$(mydirs -l | tr ':' '\t' | default-fuzzy-finder | tr '\t' ' ' | awk '{print $1}')
    else
        dir_alias=$1
    fi

    dir_path=$(mydirs -p $dir_alias)
    tmux new-session -d -s "$dir_alias" -c "$dir_path"
}


function mydirs-default-fuzzy-finder()
{
    mydirs_option=$(mydirs --list-args | tr ' ' '\n' | default-fuzzy-finder)
    echo $mydirs_option

    if [[ "${mydirs_option}" == "--open" || "${mydirs_option}" == "-o" || "${prev}" == "--remove" || "${prev}" == "-r" ]] ; then
        mydirs_args=$(mydirs -l | tr ':' ' ' | awk '{print $1}' | default-fuzzy-finder)

        mydirs ${mydirs_option} ${mydirs_args}
    else
        mydirs ${mydirs_option}
    fi
}
alias myd="mydirs-default-fuzzy-finder"

function mydirs-open-default-fuzzy-finder()
{
    mydirs_args=$(mydirs -l | tr ':' '\t' | default-fuzzy-finder | tr '\t' ' ' | awk '{print $1}')
    mydirs -o ${mydirs_args}
}
alias mk="mydirs-open-default-fuzzy-finder"
