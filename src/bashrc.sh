# Add the following lines to your bashrc:
# export MYDIRS_DIRECTORY=<path-to>/GitRepoWatcher
# source $MYDIRS_DIRECTORY/src/bashrc.sh

if [ -z "$MYDIRS_PYTHON_PATH" ];
then
    export MYDIRS_PYTHON_PATH=$MYDIRS_DIRECTORY/python/
    export PYTHONPATH=$MYDIRS_PYTHON_PATH:$PYTHONPATH
fi

alias mydirs=". "$MYDIRS_DIRECTORY"/mydirs.sh"
source $MYDIRS_DIRECTORY"/autocompletion_mydirs.sh"

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

function mytmux()
{
    dir_alias=$1
    dir_path=$(mydirs -p $dir_alias)
    tmux new -s $dir_alias -c $dir_path
}
case $SHELL in
*/zsh)
   # assume Zsh
   ;;
*/bash)
   # assume Bash
   complete -F _my mytmux
   ;;
*)


function mydirs-sk()
{
    mydirs_option=$(mydirs --list-args | tr ' ' '\n' | sk)
    echo $mydirs_option

    if [[ "${mydirs_option}" == "--open" || "${mydirs_option}" == "-o" || "${prev}" == "--remove" || "${prev}" == "-r" ]] ; then
        mydirs_args=$(mydirs -l | tr ':' ' ' | awk '{print $1}' | sk)

        mydirs ${mydirs_option} ${mydirs_args}
    else
        mydirs ${mydirs_option}
    fi
}
alias m="mydirs-sk"

function mydirs-open-sk()
{
    mydirs_args=$(mydirs -l | tr ':' '\t' | sk | tr '\t' ' ' | awk '{print $1}')
    mydirs -o ${mydirs_args}
}
alias mk="mydirs-open-sk"
