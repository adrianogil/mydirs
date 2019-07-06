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
complete -F _my mytmux

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