"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const fs_1 = require("fs");
const path_1 = require("path");
const vscode_1 = require("vscode");
const constants_1 = require("../constants");
const errorhandler_1 = require("./errorhandler");
function getGitCommand() {
    const gitConfig = vscode_1.workspace.getConfiguration("git");
    const pathCommand = gitConfig.get("path");
    const promise = new Promise((resolve, reject) => {
        if (!pathCommand) {
            resolve(constants_1.GIT_COMMAND_IN_PATH);
        }
        const commandPath = path_1.normalize(pathCommand);
        fs_1.access(commandPath, fs_1.constants.X_OK, (err) => {
            if (err) {
                errorhandler_1.ErrorHandler.logError(new Error(`Can not execute "${commandPath}" (your git.path property) falling back to "${constants_1.GIT_COMMAND_IN_PATH}"`));
                resolve(constants_1.GIT_COMMAND_IN_PATH);
            }
            else {
                resolve(commandPath);
            }
        });
    });
    return promise;
}
exports.getGitCommand = getGitCommand;
//# sourceMappingURL=gitcommand.js.map