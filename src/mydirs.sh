
if [ $1 == "-o" ] || [ $1 == "--open" ]; then
    cd_directory="$(python $MYDIRS_DIRECTORY/mydirs.py $1 $2)"
    echo "Let's go to directory "$cd_directory
    cd "$cd_directory"
else
    python $MYDIRS_DIRECTORY//mydirs.py $1 $2
fi