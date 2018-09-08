"use strict";
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : new P(function (resolve) { resolve(result.value); }).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
Object.defineProperty(exports, "__esModule", { value: true });
const vscode_1 = require("vscode");
const blame_1 = require("./git/blame");
function activate(context) {
    return __awaiter(this, void 0, void 0, function* () {
        if (vscode_1.workspace.workspaceFolders) {
            const app = new blame_1.GitBlame();
            const blameCommand = vscode_1.commands.registerCommand("gitblame.quickInfo", app.showMessage, app);
            const linkCommand = vscode_1.commands.registerCommand("gitblame.online", app.blameLink, app);
            context.subscriptions.push(app, blameCommand, linkCommand);
        }
    });
}
exports.activate = activate;
//# sourceMappingURL=index.js.map