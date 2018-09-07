local ret_status="%(?:%{$fg_bold[green]%}➜ :%{$fg_bold[red]%}➜ %s)"
PROMPT='%{$bg[none]%}%{$fg_bold[yellow]%}%n@%m %{$fg_bold[magenta]%}%d %{$fg_bold[blue]%}$(svn_prompt_info)$(git_prompt_info)%(?,,%{${fg_bold[blue]}%}%{$reset_color%}) $ret_status% %{$reset_color%}'

ZSH_THEME_GIT_PROMPT_PREFIX="git:(%{$fg[red]%}"
ZSH_THEME_GIT_PROMPT_SUFFIX="%{$reset_color%}"
ZSH_THEME_GIT_PROMPT_DIRTY="%{$fg[blue]%}) %{$fg[yellow]%}✗%{$reset_color%}"
ZSH_THEME_GIT_PROMPT_CLEAN="%{$fg[blue]%})"

local return_status="%{$fg[red]%}%(?..[%?])%{$reset_color%}"
RPROMPT='${return_status}%{$reset_color%}'
