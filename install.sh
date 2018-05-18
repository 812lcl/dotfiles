#!/usr/bin/env bash
DOTFILES_DIR=$(cd `dirname $0`; pwd)

read -p "Will you install oh-my-zsh? (y/n) " -n 1
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ ! -d $HOME/.oh-my-zsh ]; then
        git clone https://github.com/robbyrussell/oh-my-zsh.git ~/.oh-my-zsh
    fi
    if [ -d $HOME/.oh-my-zsh/themes ]; then
        cp -f $DOTFILES_DIR/robbyrussell.zsh-theme ~/.oh-my-zsh/themes/
    fi
fi

function doIt() {
    rsync --exclude ".git/" --exclude ".812lcl-vim/" --exclude "bin/" --exclude "install.sh" --exclude ".i3/" --exclude "robbyrussell.zsh-theme"\
         --exclude "vimrc-lcl" --exclude "README.md" --exclude "rsync.sh" --exclude "smb.conf" -av --no-perms $DOTFILES_DIR/ ~
    if [ -d /etc/samba ]; then
        cp $DOTFILES_DIR/smb.conf /etc/samba/
    fi
    source ~/.zshrc
}

if [ "$1" == "--force" -o "$1" == "-f" ]; then
    doIt
else
    read -p "This may overwrite existing files in your home directory. Are you sure? (y/n) " -n 1
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        doIt
    fi
fi
unset doIt

read -p "Will you install vim? (y/n) " -n 1
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    $DOTFILES_DIR/.812lcl-vim/install.sh
fi

read -p "Will you install i3wm? (y/n) " -n 1
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rsync -av --no-perms $DOTFILES_DIR/.i3 ~
fi
