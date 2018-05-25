"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const vscode = require("vscode");
const path_1 = require("path");
class OutlineProvider {
    constructor(data, filter) {
        this.data = data;
        this.filter = filter;
        this._onDidChangeTreeData = new vscode.EventEmitter();
        this.onDidChangeTreeData = this._onDidChangeTreeData.event;
        this.refresh();
    }
    refresh() {
        this._onDidChangeTreeData.fire();
    }
    getTreeItem(element) {
        return element;
    }
    getChildren(element) {
        return new Promise(resolve => {
            if (element) {
                resolve(this.buildList(element.ref.label));
            }
            else {
                resolve(this.buildList());
            }
        });
    }
    buildList(receiver) {
        let list = Array();
        this.data.forEach(i => {
            if (receiver && receiver !== i.receiver) {
                return;
            }
            switch (i.type) {
                case "type":
                    let collapsable = (this.data.some(x => x.receiver === i.label)) ? vscode.TreeItemCollapsibleState.Collapsed : vscode.TreeItemCollapsibleState.None;
                    list.push(new GoOutlineItem(i.label, i, collapsable));
                    break;
                default:
                    if (receiver || this.filter !== "type") {
                        list.push(new GoOutlineItem(i.label, i, vscode.TreeItemCollapsibleState.None));
                    }
            }
        });
        return list;
    }
}
exports.OutlineProvider = OutlineProvider;
const iconsRootPath = path_1.join(path_1.dirname(__dirname), 'resources', 'icons');
function getIcons(iconName) {
    return {
        light: vscode.Uri.file(path_1.join(iconsRootPath, "light", `${iconName}.svg`)),
        dark: vscode.Uri.file(path_1.join(iconsRootPath, "dark", `${iconName}.svg`))
    };
}
class GoOutlineItem extends vscode.TreeItem {
    constructor(label, ref, collapsibleState) {
        super(label, collapsibleState);
        this.label = label;
        this.ref = ref;
        this.collapsibleState = collapsibleState;
    }
    get iconPath() {
        switch (this.ref.type) {
            case "type":
                return getIcons("class");
            case "var":
                return getIcons("field");
            case "const":
                return getIcons("constant");
            case "func":
                return getIcons("method");
            default:
                return getIcons("method");
        }
    }
    get command() {
        return {
            title: "Open File",
            command: "extension.OutlinerOpenItem",
            arguments: [this.ref]
        };
    }
}
exports.GoOutlineItem = GoOutlineItem;
//# sourceMappingURL=provider.js.map