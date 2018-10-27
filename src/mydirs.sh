
if [ $1 == "-o" ] || [ $1 == "--open" ] || [ $1 == "--back" ] ||  [ $1 == "-bk" ]; then
    cd_directory="$(python $MYDIRS_DIRECTORY/mydirs.py $1 $2)"
    echo "Let's go to directory "$cd_directory
    cd "$cd_directory"
else
    python2 $MYDIRS_DIRECTORY//mydirs.py $1 $2
fi