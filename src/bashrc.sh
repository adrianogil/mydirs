alias mydirs=". "$MYDIRS_DIRECTORY"/mydirs.sh"
source $MYDIRS_DIRECTORY"/autocompletion_mydirs.sh"

function mydirs-rnd()
{
    mydirs -o $(mydirs -l | gshuf -n1 | sed 's/:/ /g' | awk '{print $1}')
}