# zsh profiling
# zmodload zsh/datetime
# setopt PROMPT_SUBST
# PS4='+$EPOCHREALTIME %N:%i> '
#
# logfile=$(mktemp zsh_profile.XXXXXXXX)
# echo "Logging to $logfile"
# exec 3>&2 2>$logfile
#
# setopt XTRACE

# source /usr/local/share/antigen/antigen.zsh
source /opt/homebrew/share/antigen/antigen.zsh

# Load the oh-my-zsh's library.
antigen use oh-my-zsh

# Bundles from the default repo (robbyrussell's oh-my-zsh).
antigen bundle git
antigen bundle brew
antigen bundle osx
antigen bundle virtualenv
antigen bundle virtualenvwrapper
antigen bundle colored-man-pages

# antigen bundle command-not-found
# if brew command command-not-found-init > /dev/null 2>&1; then eval "$(brew command-not-found-init)"; fi

antigen bundle zsh-users/zsh-syntax-highlighting
antigen bundle zsh-users/zsh-autosuggestions
antigen bundle skywind3000/z.lua
# antigen bundle hchbaw/auto-fu.zsh

# Load the theme.
# antigen theme robbyrussell

# Tell Antigen that you're done.
antigen apply

export _ZL_ROOT_MARKERS=".git,.svn,.hg,.root,package.json,.gitignore,ci.json,config-ci.json"

# User configuration
unset GREP_OPTIONS
export GOROOT=/opt/homebrew/opt/go/libexec
export GOPATH=$HOME/go
export GOBIN=$GOPATH/bin
export PATH=/opt/homebrew/bin:/usr/local/bin:/usr/local/sbin:$HOME/bin:$PATH:/usr/local/opt/go/libexec/bin:$GOBIN

PATH="/usr/local/opt/coreutils/libexec/gnubin:$PATH"
MANPATH="/usr/local/opt/coreutils/libexec/gnuman:${MANPATH-/usr/share/man}"
PATH="/usr/local/opt/gnu-getopt/bin:$PATH"
MANPATH="/usr/local/opt/gnu-getopt/share/man:$MANPATH"
PATH="/usr/local/opt/findutils/bin:$PATH"
MANPATH="/usr/local/opt/findutils/share/man:$MANPATH"
PATH="/usr/local/opt/gnu-sed/libexec/gnubin:$PATH"
MANPATH="/usr/local/opt/gnu-sed/libexec/gnuman:${MANPATH-/usr/share/man}"
export MANPATH="/usr/local/share/man:/usr/local/man:$MANPATH"
#PATH="/usr/local/opt/python/bin:/usr/local/opt/python/libexec/bin:$PATH"


# bindkey -v
bindkey -M viins '\e.' insert-last-word
bindkey -M viins '\e^?' backward-kill-word
bindkey -M viins '\eb' backward-word
bindkey -M viins '\ef' forward-word
bindkey -M viins "^e" end-of-line
bindkey -M viins "^a" beginning-of-line
bindkey -M viins "^w" backward-kill-word
bindkey -M viins "^h" backward-delete-char      # Control-h also deletes the previous char
bindkey -M viins "^u" backward-kill-line
bindkey -M viins "^k" kill-line
bindkey -v '^?' backward-delete-char

unsetopt correct_all
setopt correct

export CLICOLOR=1
export LANG=en_US.UTF-8

export ZSH_AUTOSUGGEST_HIGHLIGHT_STYLE='fg=white'
export ZSH_HIGHLIGHT_HIGHLIGHTERS=(main brackets pattern cursor)

# enable c-s in vim
stty -ixon

source ~/.aliases
source ~/.exports
source ~/.function.sh

if [ -n "$BASH_VERSION" ]; then
    export PS1="\[$(tput bold)\]\[$(tput setaf 1)\][\[$(tput setaf 3)\]\u\[$(tput setaf 2)\]@\[$(tput setaf 4)\]\h \[$(tput setaf 5)\]\W\[$(tput setaf 1)\]]\[$(tput setaf 7)\]\\$ \[$(tput sgr0)\]" 
else
    local ret_status="%(?:%{$fg_bold[green]%}➜ :%{$fg_bold[red]%}➜ )"
    ZSH_THEME_GIT_PROMPT_PREFIX="%{$fg_bold[blue]%}\uE0A0:(%{$fg[red]%}"
    ZSH_THEME_GIT_PROMPT_SUFFIX="%{$reset_color%} "
    ZSH_THEME_GIT_PROMPT_DIRTY="%{$fg[blue]%}) %{$fg[yellow]%}✗"
    ZSH_THEME_GIT_PROMPT_CLEAN="%{$fg[blue]%})"
    #export PROMPT='%f%{$fg_bold[cyan]%}$(_fish_collapsed_pwd)%{$reset_color%}%f $(git_prompt_info)${ret_status}'
    # PROMPT='%{$fg_bold[red]%}[%{$fg[yellow]%}%n%{$fg[green]%}@%{$fg[blue]%}%m%{$reset_color%} %{$fg_bold[magenta]%}$(_fish_collapsed_pwd)%{$fg_bold[red]%}]%{$reset_color%} ${ret_status}'
    PROMPT='%{$fg_bold[red]%}[%{$fg[yellow]%}%n%{$fg[green]%}@%{$fg[blue]%}%m%{$reset_color%} %{$fg_bold[magenta]%}$(_fish_collapsed_pwd)%{$fg_bold[red]%}]%{$reset_color%}%{$fg_bold[cyan]%}$(virtualenv_prompt_info) $(git_prompt_info)${ret_status}'
    local return_status="%{$fg[red]%}%(?..[%?])%{$reset_color%}"
    RPROMPT='${return_status}%{$reset_color%}'
fi

export FZF_DEFAULT_OPTS="--height 40% --layout=reverse --preview '(highlight -O ansi {} || cat {}) 2> /dev/null | head -500'"

[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh

# zsh profiling
# unsetopt XTRACE
# exec 2>&3 3>&-

# The next line updates PATH for the Google Cloud SDK.
if [ -f '$HOME/Downloads/google-cloud-sdk/path.zsh.inc' ]; then . '$HOME/Downloads/google-cloud-sdk/path.zsh.inc'; fi

# The next line enables shell command completion for gcloud.
if [ -f '$HOME/Downloads/google-cloud-sdk/completion.zsh.inc' ]; then . '$HOME/Downloads/google-cloud-sdk/completion.zsh.inc'; fi

go env -w GO111MODULE=on
export PROTO_PATH=/usr/local/protoc
export PATH=$PATH:$PROTO_PATH/bin
export PATH="/opt/homebrew/opt/openjdk@17/bin:$PATH"
export PATH="/opt/homebrew/opt/openjdk/bin:$PATH"
