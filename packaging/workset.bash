# Completions for workset (bash)

_workset() {
    local cur prev words cword
    _init_completion || return

    local commands="list apply validate doctor default picker edit capture duplicate"
    if [[ ${cword} -eq 1 ]]; then
        COMPREPLY=( $(compgen -W "${commands}" -- "${cur}") )
        return
    fi

    case "${words[1]}" in
        apply|edit|duplicate)
            local profiles
            profiles=$(workset list 2>/dev/null | awk '{print $1}')
            COMPREPLY=( $(compgen -W "${profiles}" -- "${cur}") )
            ;;
    esac
}

complete -F _workset workset
