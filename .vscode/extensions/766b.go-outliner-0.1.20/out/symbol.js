'use strict';
Object.defineProperty(exports, "__esModule", { value: true });
const vscode = require("vscode");
const path_1 = require("path");
var ItemType;
(function (ItemType) {
    ItemType["None"] = "none";
    ItemType["Type"] = "type";
    ItemType["Func"] = "func";
    ItemType["Var"] = "var";
    ItemType["Const"] = "const";
})(ItemType = exports.ItemType || (exports.ItemType = {}));
const iconsRootPath = path_1.join(path_1.dirname(__dirname), 'resources', 'icons');
function getIcons(iconName) {
    return {
        light: vscode.Uri.file(path_1.join(iconsRootPath, "light", `${iconName}.svg`)),
        dark: vscode.Uri.file(path_1.join(iconsRootPath, "dark", `${iconName}.svg`))
    };
}
class Symbol {
    constructor() {
        this.label = "";
        this.type = "";
        this.receiver = "";
        this.file = "";
        this.start = 0;
        this.end = 0;
        this.line = 0;
        this.collapsibleState = vscode.TreeItemCollapsibleState.None;
        this.rootType = ItemType.None;
    }
    get contextValue() { return 'symbol'; }
    get command() {
        if (this.rootType !== ItemType.None) {
            return undefined;
        }
        return {
            title: "Open File",
            command: "goOutliner.OpenItem",
            arguments: [this]
        };
    }
    get iconPath() {
        if (this.rootType !== ItemType.None) {
            return undefined;
        }
        switch (this.type) {
            case "type":
                return getIcons("class");
            case "var":
                return getIcons("field");
            case "const":
                return getIcons("constant");
            case "func":
                return getIcons("method");
            default:
                return undefined;
        }
    }
    get isTestFile() {
        return this.file.toLowerCase().endsWith("_test.go");
    }
    static fromObject(src) {
        return Object.assign(new Symbol(), src);
    }
    static NewRootItem(type) {
        let s = new Symbol;
        switch (type) {
            case ItemType.Func:
                s.label = "Functions";
                break;
            case ItemType.Const:
                s.label = "Constants";
                break;
            case ItemType.Var:
                s.label = "Variables";
                break;
            case ItemType.Type:
                s.label = "Types";
                break;
        }
        s.rootType = type;
        s.collapsibleState = vscode.TreeItemCollapsibleState.Collapsed;
        return s;
    }
}
exports.Symbol = Symbol;
//# sourceMappingURL=symbol.js.map