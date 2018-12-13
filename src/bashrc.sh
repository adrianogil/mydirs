alias mydirs=". "$MYDIRS_DIRECTORY"/mydirs.sh"
source $MYDIRS_DIRECTORY"/autocompletion_mydirs.sh"

alias my="mydirs -o"

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