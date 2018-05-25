"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const vscode_1 = require("vscode");
const filedummy_1 = require("./filedummy");
const filephysical_1 = require("./filephysical");
class GitFileFactory {
    static create(fileName, disposeCallback) {
        if (GitFileFactory.inWorkspace(fileName)) {
            return new filephysical_1.GitFilePhysical(fileName, disposeCallback);
        }
        else {
            return new filedummy_1.GitFileDummy(fileName, disposeCallback);
        }
    }
    static inWorkspace(fileName) {
        const uriFileName = vscode_1.Uri.file(fileName);
        return typeof vscode_1.workspace.getWorkspaceFolder(uriFileName) !== "undefined";
    }
}
exports.GitFileFactory = GitFileFactory;
//# sourceMappingURL=filefactory.js.map