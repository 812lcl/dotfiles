'use strict';
Object.defineProperty(exports, "__esModule", { value: true });
const vscode = require("vscode");
const symbol_1 = require("./symbol");
var ProviderType;
(function (ProviderType) {
    ProviderType["Main"] = "Main";
    ProviderType["Tests"] = "Tests";
    ProviderType["Benchmarks"] = "Benchmarks";
})(ProviderType = exports.ProviderType || (exports.ProviderType = {}));
class Provider {
    constructor(providerType, event) {
        this.providerType = providerType;
        this.event = event;
        this._onDidChangeTreeData = new vscode.EventEmitter();
        this.onDidChangeTreeData = this._onDidChangeTreeData.event;
        this.symbols = new Array();
        this.event(x => this.update(x));
    }
    getTreeItem(element) {
        return element;
    }
    update(symbols) {
        this.symbols = symbols;
        vscode.commands.executeCommand('setContext', `showGoOutliner${this.providerType}View`, symbols.length > 0);
        this._onDidChangeTreeData.fire();
    }
    rootItems() {
        let list = Array();
        if (this.symbols.length === 0) {
            let note = new symbol_1.Symbol();
            note.label = "No results.";
            note.collapsibleState = vscode.TreeItemCollapsibleState.None;
            list.push(note);
        }
        else {
            [symbol_1.ItemType.Type, symbol_1.ItemType.Func, symbol_1.ItemType.Var, symbol_1.ItemType.Const].forEach(e => {
                if (this.countType(e) > 0) {
                    list.push(symbol_1.Symbol.NewRootItem(e));
                }
            });
        }
        return new Promise(resolve => resolve(list));
    }
    buildItemList(element) {
        let list = Array();
        switch (this.providerType) {
            case ProviderType.Tests:
                list = this.symbols;
                break;
            case ProviderType.Benchmarks:
                list = this.symbols;
                break;
            default:
                if (element) {
                    if (element.rootType !== symbol_1.ItemType.None) {
                        switch (element.rootType) {
                            case symbol_1.ItemType.Type:
                                list = this.symbols.filter(x => x.type === element.rootType && !x.receiver);
                                list.map(x => {
                                    x.collapsibleState = this.symbols.some(y => y.receiver === x.label) ? vscode.TreeItemCollapsibleState.Collapsed : vscode.TreeItemCollapsibleState.None;
                                });
                                break;
                            case symbol_1.ItemType.Func:
                                list = this.symbols.filter(x => x.type === element.rootType && !x.receiver);
                                break;
                            default:
                                list = this.symbols.filter(x => x.type === element.rootType);
                                break;
                        }
                    }
                    else {
                        list = this.symbols.filter(x => element.label === x.receiver);
                    }
                }
                break;
        }
        return new Promise(resolve => resolve(list));
    }
    getChildren(element) {
        if (!element && this.providerType === ProviderType.Main) {
            return this.rootItems();
        }
        return this.buildItemList(element);
    }
    countType(type) {
        let num = 0;
        this.symbols.forEach(x => {
            // Skip functions that have receiver
            if (type === symbol_1.ItemType.Func && x.receiver) {
                return;
            }
            if (x.type === type) {
                num++;
            }
        });
        return num;
    }
    dispose() {
        this._onDidChangeTreeData.dispose();
    }
}
exports.Provider = Provider;
//# sourceMappingURL=provider.js.map