_mydirs()
{
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    opts="--save -s --open -o --remove -r --list -l --path -p"
    _script_folders=$(python3 -m mydirs --auto-list)

	if [[ "${prev}" == "--open" || "${prev}" == "-o" || "${prev}" == "--remove" || "${prev}" == "-r" || "${prev}" == "--path" || "${prev}" == "-p"  ]] ; then
		COMPREPLY=( $(compgen -W "${_script_folders}" -- ${cur}) )
        return 0
	fi

    if [[ ${cur} == -* ]] ; then
        COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
        return 0
    fi
}
complete -F _mydirs mydirs

_my()
{
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    opts="--save -s --open -o --remove -r --list -l --path -p"
    _script_folders=$(python3 -m mydirs --auto-list)
        
    COMPREPLY=( $(compgen -W "${_script_folders}" -- ${cur}) )
}
complete -F _my my