macOS 系统:
用户配置: ~/Library/Application Support/Cursor/User/settings.json
快捷键: ~/Library/Application Support/Cursor/User/keybindings.json
扩展: ~/.cursor/extensions

使用命令行导出扩展列表
你也可以导出已安装扩展的列表:

# 导出扩展列表
cursor --list-extensions > extensions.txt

# 在新电脑上批量安装
cat extensions.txt | xargs -L 1 cursor --install-extension
