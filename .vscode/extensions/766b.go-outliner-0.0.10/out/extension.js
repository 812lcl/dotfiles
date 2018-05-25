'use strict';
Object.defineProperty(exports, "__esModule", { value: true });
const vscode = require("vscode");
const cmd_1 = require("./cmd");
function activate(context) {
    const rootPath = vscode.workspace.rootPath;
    if (!rootPath) {
        vscode.window.showErrorMessage('Workspace is not set');
        return;
    }
    const p = new cmd_1.GoOutliner(rootPath);
    cmd_1.goOutlinerInstalled().then(x => {
        let opt = "Install";
        switch (x) {
            case -2: // Not installed
                break;
            case -1: // Older version installed
                opt = "Update";
                break;
            default:
                return;
        }
        vscode.window.showInformationMessage(`Go-Outliner: ${opt} Package`, opt).then(s => {
            if (s === "Install" || s === "Update") {
                cmd_1.installGoOutliner().then(x => {
                    if (x) {
                        p.Reload();
                    }
                    else {
                        vscode.window.showErrorMessage("Could not get go-outliner package.");
                    }
                });
            }
        });
    });
    p.onDidChangeJSON(e => {
        vscode.window.registerTreeDataProvider('typeView', p.Types());
        vscode.window.registerTreeDataProvider('funcView', p.Funcs());
        vscode.window.registerTreeDataProvider('varView', p.Variables());
    });
    vscode.workspace.onDidSaveTextDocument(() => {
        p.Reload();
    });
    vscode.window.onDidChangeActiveTextEditor(() => {
        let e = vscode.window.activeTextEditor;
        if (!e) {
            return;
        }
        p.Reload(e.document.fileName);
    });
    vscode.commands.registerCommand('extension.OutlinerOpenItem', (ref) => {
        let f = vscode.Uri.file(ref.file);
        vscode.commands.executeCommand("vscode.open", f).then(ok => {
            let editor = vscode.window.activeTextEditor;
            if (!editor) {
                return;
            }
            let pos = new vscode.Position(ref.line - 1, 0);
            editor.selection = new vscode.Selection(pos, pos);
            editor.revealRange(new vscode.Range(pos, pos), vscode.TextEditorRevealType.AtTop);
        });
    });
}
exports.activate = activate;
function deactivate() {
}
exports.deactivate = deactivate;
//# sourceMappingURL=extension.js.map