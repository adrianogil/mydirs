
if [[ $1 == "-o" ]] || [[ $1 == "--open" ]] || [[ $1 == "--back" ]] ||  [[ $1 == "-bk" ]]; then
    cd_directory="$(python3 -m mydirs $1 $2)"
    echo "Let's go to directory "$cd_directory
    cd "$cd_directory"
else
    python3 -m mydirs $1 $2
fi
