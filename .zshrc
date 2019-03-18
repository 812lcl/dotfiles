source /usr/local/share/antigen/antigen.zsh

# Load the oh-my-zsh's library.
antigen use oh-my-zsh

# Bundles from the default repo (robbyrussell's oh-my-zsh).
antigen bundle git
antigen bundle autojump
antigen bundle brew
antigen bundle osx
antigen bundle colored-man-pages
antigen bundle command-not-found

antigen bundle zsh-users/zsh-syntax-highlighting
antigen bundle zsh-users/zsh-autosuggestions

# Load the theme.
antigen theme robbyrussell

# Tell Antigen that you're done.
antigen apply

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

# bindkey -v
bindkey -M viins '\e.' insert-last-word
bindkey -M viins '\e^?' backward-kill-word
bindkey -M viins '\eb' backward-word
bindkey -M viins '\ef' forward-word
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

export WORKON_HOME=$HOME/.virtualenvs
export VIRTUALENVWRAPPER_PYTHON=/usr/local/opt/python@2/bin/python
source /usr/local/bin/virtualenvwrapper.sh
stty -ixon

source ~/.aliases
source ~/.exports
