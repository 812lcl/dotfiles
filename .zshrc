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
#antigen bundle virtualenvwrapper
antigen bundle colored-man-pages
antigen bundle darvid/zsh-poetry

# antigen bundle command-not-found
# if brew command command-not-found-init > /dev/null 2>&1; then eval "$(brew command-not-found-init)"; fi

antigen bundle darvid/zsh-poetry
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
#    PROMPT='%{$fg_bold[red]%}[%{$fg[yellow]%}%n%{$fg[green]%}@%{$fg[blue]%}%m%{$reset_color%} %{$fg_bold[magenta]%}$(_fish_collapsed_pwd)%{$fg_bold[red]%}]%{$reset_color%} $(git_prompt_info)${ret_status}'
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
export PATH="/opt/homebrew/opt/openjdk/bin:$PATH"
export JAVA_HOME=/opt/homebrew/opt/openjdk
export PATH=$HOME/.local/bin:$JAVA_HOME/bin:$PATH

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion

# pnpm
export PNPM_HOME="/Users/liuchunlei/Library/pnpm"
case ":$PATH:" in
  *":$PNPM_HOME:"*) ;;
  *) export PATH="$PNPM_HOME:$PATH" ;;
esac
# pnpm end
export PATH="/opt/homebrew/opt/mysql@8.4/bin:$PATH"
export GRADLE="/opt/homebrew/opt/gradle"

export WORKON_HOME=$HOME/.virtualenvs
source /opt/homebrew/opt/virtualenvwrapper/bin/virtualenvwrapper.sh

# Added by Windsurf
export PATH="/Users/liuchunlei/.codeium/windsurf/bin:$PATH"
# >>> xmake >>>
test -f "/Users/liuchunlei/.xmake/profile" && source "/Users/liuchunlei/.xmake/profile"
# <<< xmake <<<
# # >>> conda initialize >>>
# # !! Contents within this block are managed by 'conda init' !!
# __conda_setup="$('/opt/anaconda3/bin/conda' 'shell.zsh' 'hook' 2> /dev/null)"
# if [ $? -eq 0 ]; then
#     eval "$__conda_setup"
# else
#     if [ -f "/opt/anaconda3/etc/profile.d/conda.sh" ]; then
#         . "/opt/anaconda3/etc/profile.d/conda.sh"
#     else
#         export PATH="/opt/anaconda3/bin:$PATH"
#     fi
# fi
# unset __conda_setup
# # <<< conda initialize <<<

export GEMINI_API_KEY=

export NODE_EXTRA_CA_CERTS=$HOME/.node-certs/ISRG\ Root\ X1.pem
export NODE_OPTIONS="--dns-result-order=ipv4first"

# Set these in your shell (e.g., ~/.bashrc, ~/.zshrc)
#export ANTHROPIC_BASE_URL="https://openrouter.ai/api"
#export ANTHROPIC_AUTH_TOKEN=""
export ANTHROPIC_BASE_URL="http://127.0.0.1:3456"
export ANTHROPIC_AUTH_TOKEN="test"
export ANTHROPIC_API_KEY="" # Important: Must be explicitly empty


# Claude Code 安全设置
export CLAUDE_PERMISSIONS_FILE="$HOME/.claude/permissions.json"
export CLAUDE_SECURITY_LEVEL="balanced"
export CLAUDE_LOG_LEVEL="info"
export CLAUDE_CONFIG_DIR="$HOME/.claude"

# Claude Code agents 路径
export CLAUDE_AGENTS_PATH="$HOME/.claude/agents"


# opencode
export PATH=/Users/liuchunlei/.opencode/bin:$PATH
