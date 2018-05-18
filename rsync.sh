#!/usr/bin/env bash
DOTFILES_DIR=$(cd `dirname $0`; pwd)
copy="rsync --exclude ".git/" --exclude ".gitignore" --exclude "bundle" --exclude ".netrwhist" --exclude ".vimtmp"\
    --exclude "view" --exclude "sessions" -av --delete"
for i in $HOME/.812lcl-vim $HOME/.i3 $HOME/bin $HOME/.vim/vimrc-lcl $HOME/.Xdefaults $HOME/.Xmodmap $HOME/.zshrc $HOME/.aliases $HOME/.exports $HOME/.gitconfig $HOME/.tmux.conf $HOME/.bashrc /etc/samba/smb.conf; do [ -e $i ] && [ ! -L $i ] && $copy $i $DOTFILES_DIR/; done
