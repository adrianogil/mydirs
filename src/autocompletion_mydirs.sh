_mydirs() 
{
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    opts="--save -s --open -o --remove -r --list -l"
    _script_folders=$(/Users/gil/workspace/python/mydirs/src/mydirs.py --auto-list)

	if [[ "${prev}" == "--open" || "${prev}" == "-o" || "${prev}" == "--remove" || "${prev}" == "-r"  ]] ; then
		COMPREPLY=( $(compgen -W "${_script_folders}" -- ${cur}) )
        return 0
	fi

    if [[ ${cur} == -* ]] ; then
        COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
        return 0
    fi
}
complete -F _mydirs mydirs