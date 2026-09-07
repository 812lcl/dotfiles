#loginPath

# Ensure login shells started inside a direnv-managed repo also pick up
# the current directory's exports, so non-interactive shells see BRAIN_DIR.
if command -v direnv >/dev/null 2>&1; then
  eval "$(direnv export zsh 2>/dev/null)"
fi

# Initialization for FDK command line tools.Sat Oct  4 11:28:52 2014
FDK_EXE="/Users/812lcl/bin/FDK/Tools/osx"
PATH=${PATH}:"/Users/812lcl/bin/FDK/Tools/osx"
export PATH
export FDK_EXE

# Added by OrbStack: command-line tools and integration
# This won't be added again if you remove it.
source ~/.orbstack/shell/init.zsh 2>/dev/null || :

# Added by Obsidian
export PATH="$PATH:/Applications/Obsidian.app/Contents/MacOS"

export PATH="/Users/liuchunlei/.local/bin:$PATH"
