
if [[ $1 == "-o" ]] || [[ $1 == "--open" ]] || [[ $1 == "--back" ]] ||  [[ $1 == "-bk" ]]; then
    previous_directory="$PWD"
    if ! cd_directory="$(python3 -m mydirs "$@")"; then
        return 1
    fi
    echo "Let's go to directory $cd_directory"
    if ! cd "$cd_directory"; then
        return 1
    fi
    if [[ $1 == "-o" ]] || [[ $1 == "--open" ]]; then
        python3 -m mydirs --record-open "$2" "$previous_directory" "$PWD"
    fi
else
    python3 -m mydirs "$@"
fi
