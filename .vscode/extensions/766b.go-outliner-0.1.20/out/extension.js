'use strict';
Object.defineProperty(exports, "__esModule", { value: true });
const vscode = require("vscode");
const app_1 = require("./app");
function activate(ctx) {
    const app = new app_1.AppExec(ctx);
    ctx.subscriptions.push(app);
    ctx.subscriptions.push(registerCommands(app.terminal));
}
exports.activate = activate;
function deactivate() {
}
exports.deactivate = deactivate;
function registerCommands(terminal) {
    let subscriptions = [];
    subscriptions.push(vscode.commands.registerCommand('goOutliner.OpenItem', (ref) => {
        let f = vscode.Uri.file(ref.file);
        vscode.commands.executeCommand("vscode.open", f).then(ok => {
            let editor = vscode.window.activeTextEditor;
            if (!editor) {
                return;
            }
            let pos = new vscode.Position(ref.line - 1, 0);
            editor.selection = new vscode.Selection(pos, pos);
            editor.revealRange(new vscode.Range(pos, pos), vscode.TextEditorRevealType.InCenter);
        });
    }));
    subscriptions.push(vscode.commands.registerCommand('goOutliner.Test', (ref) => {
        terminal.TestFunc(ref.label);
    }));
    subscriptions.push(vscode.commands.registerCommand('goOutliner.TestAll', (ref) => {
        terminal.TestFunc();
    }));
    subscriptions.push(vscode.commands.registerCommand('goOutliner.Benchmark', (ref) => {
        terminal.BenchmarkFunc(ref.label);
    }));
    subscriptions.push(vscode.commands.registerCommand('goOutliner.BenchmarkAll', (ref) => {
        terminal.BenchmarkFunc();
    }));
    return vscode.Disposable.from(...subscriptions);
}
//# sourceMappingURL=extension.js.map