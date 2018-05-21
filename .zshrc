# Path to your oh-my-zsh configuration.
ZSH=$HOME/.oh-my-zsh
DISABLE_UPDATE_PROMPT=true

# Set name of the theme to load.
# Look in ~/.oh-my-zsh/themes/
# Optionally, if you set this to "random", it'll load a random theme each
# time that oh-my-zsh is loaded.
# ZSH_THEME="robbyrussell"
ZSH_THEME="powerlevel9k/powerlevel9k"

POWERLEVEL9K_LEFT_PROMPT_ELEMENTS=(dir dir_writable vcs vi_mode)
POWERLEVEL9K_RIGHT_PROMPT_ELEMENTS=(status root_indicator background_jobs ssh virtualenv go_version history)
POWERLEVEL9K_MODE='nerdfont-complete'
POWERLEVEL9K_VCS_HIDE_TAGS='true'

# dir
POWERLEVEL9K_SHORTEN_DIR_LENGTH=1
POWERLEVEL9K_SHORTEN_DELIMITER=""
POWERLEVEL9K_SHORTEN_STRATEGY="truncate_from_right"

# POWERLEVEL9K_COLOR_SCHEME='dark'
# # Advanced `context` color customization
# POWERLEVEL9K_CONTEXT_DEFAULT_FOREGROUND='233'
# POWERLEVEL9K_CONTEXT_DEFAULT_BACKGROUND='245'
# # Advanced `dir` color customization
# POWERLEVEL9K_DIR_DEFAULT_FOREGROUND='white'
# POWERLEVEL9K_DIR_DEFAULT_BACKGROUND='241'
# POWERLEVEL9K_DIR_HOME_FOREGROUND='white'
# POWERLEVEL9K_DIR_HOME_BACKGROUND='241'
# POWERLEVEL9K_DIR_HOME_SUBFOLDER_FOREGROUND='white'
# POWERLEVEL9K_DIR_HOME_SUBFOLDER_BACKGROUND='241'
# # Advanced `vcs` color customization
# POWERLEVEL9K_VCS_CLEAN_FOREGROUND='green'
# POWERLEVEL9K_VCS_CLEAN_BACKGROUND='238'
# POWERLEVEL9K_VCS_UNTRACKED_FOREGROUND='yellow'
# POWERLEVEL9K_VCS_UNTRACKED_BACKGROUND='238'
# POWERLEVEL9K_VCS_MODIFIED_FOREGROUND='red'
# POWERLEVEL9K_VCS_MODIFIED_BACKGROUND='238'

# Example aliases
# alias zshconfig="mate ~/.zshrc"
# alias ohmyzsh="mate ~/.oh-my-zsh"

# Set to this to use case-sensitive completion
# CASE_SENSITIVE="true"

# Uncomment this to disable bi-weekly auto-update checks
# DISABLE_AUTO_UPDATE="true"

# Uncomment to change how often before auto-updates occur? (in days)
# export UPDATE_ZSH_DAYS=13

# Uncomment following line if you want to disable colors in ls
# DISABLE_LS_COLORS="true"

# Uncomment following line if you want to disable autosetting terminal title.
# DISABLE_AUTO_TITLE="true"

# Uncomment following line if you want to disable command autocorrection
# DISABLE_CORRECTION="true"

# Uncomment following line if you want red dots to be displayed while waiting for completion
# COMPLETION_WAITING_DOTS="true"

# Uncomment following line if you want to disable marking untracked files under
# VCS as dirty. This makes repository status check for large repositories much,
# much faster.
# DISABLE_UNTRACKED_FILES_DIRTY="true"

# Uncomment following line if you want to  shown in the command execution time stamp
# in the history command output. The optional three formats: "mm/dd/yyyy"|"dd.mm.yyyy"|
# yyyy-mm-dd
# HIST_STAMPS="mm/dd/yyyy"

# Which plugins would you like to load? (plugins can be found in ~/.oh-my-zsh/plugins/*)
# Custom plugins may be added to ~/.oh-my-zsh/custom/plugins/
# Example format: plugins=(rails git textmate ruby lighthouse)
plugins=(git vi-mode autojump brew docker docker-compose docker-machine osx golang cp colored-man-pages  git-flow hub history-substring-search zsh-autosuggestions zsh-syntax-highlighting)

bindkey -M viins '\e.' insert-last-word
bindkey -M viins '\e^?' backward-kill-word
bindkey -v '^?' backward-delete-char
bindkey "^w" backward-kill-word
bindkey "^h" backward-delete-char      # Control-h also deletes the previous char
bindkey "^u" backward-kill-line
bindkey "^k" kill-line

source $ZSH/oh-my-zsh.sh

# User configuration

unset GREP_OPTIONS
export GOROOT=/usr/local/opt/go/libexec
export GOPATH=/Users/812lcl/go
export PATH=/usr/local/bin:/usr/local/sbin:$HOME/bin:$PATH:/usr/local/opt/go/libexec/bin:$GOPATH/bin:$GOPATH/src/gitlab.myteksi.net/gophers/go/scripts:$HOME/Code/arcanist/bin:$HOME/Code/FlameGraph
source $HOME/Code/arcanist/resources/shell/bash-completion
if brew list | grep -q coreutils > /dev/null ; then
    PATH="$(brew --prefix coreutils)/libexec/gnubin:$PATH"
    MANPATH="$(brew --prefix coreutils)/libexec/gnuman:${MANPATH-/usr/share/man}"
    eval `gdircolors -b $HOME/.dir_colors`
fi
if brew list | grep -q gnu-getopt > /dev/null ; then
    PATH="$(brew --prefix gnu-getopt)/bin:$PATH"
    MANPATH="$(brew --prefix gnu-getopt)/share/man:$MANPATH"
fi
if brew list | grep -q findutils > /dev/null ; then
    PATH="$(brew --prefix findutils)/bin:$PATH"
    MANPATH="$(brew --prefix findutils)/share/man:$MANPATH"
fi
export MANPATH="/usr/local/share/man:/usr/local/man:$MANPATH"

# # Preferred editor for local and remote sessions
# if [[ -n $SSH_CONNECTION ]]; then
#   export EDITOR='vim'
# else
#   export EDITOR='mvim'
# fi

# Compilation flags
# export ARCHFLAGS="-arch x86_64"

# ssh
# export SSH_KEY_PATH="~/.ssh/dsa_id"

# bindkey -v
unsetopt correct_all
setopt correct

source ~/.aliases
source ~/.exports

export CLICOLOR=1
export LANG=en_US.UTF-8

export ZSH_AUTOSUGGEST_HIGHLIGHT_STYLE='fg=white'
export ZSH_HIGHLIGHT_HIGHLIGHTERS=(main brackets pattern cursor)

export WORKON_HOME=$HOME/.virtualenvs
export VIRTUALENVWRAPPER_PYTHON=/usr/local/opt/python2/bin/python
source /usr/local/bin/virtualenvwrapper.sh
