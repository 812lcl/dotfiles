"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const errorhandler_1 = require("../util/errorhandler");
const file_1 = require("./file");
class GitFileDummy extends file_1.GitFile {
    constructor(fileName, disposeCallback) {
        super(fileName, disposeCallback);
        this.startCacheInterval();
        errorhandler_1.ErrorHandler.logInfo(`Will not try to blame file "${this.fileName.fsPath}" as it is outside of the current workspace`);
    }
}
exports.GitFileDummy = GitFileDummy;
//# sourceMappingURL=filedummy.js.map