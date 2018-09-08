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
const constants_1 = require("../constants");
const errorhandler_1 = require("../util/errorhandler");
const blame_1 = require("./blame");
class GitFile {
    constructor(fileName, disposeCallback) {
        this.fileName = vscode_1.Uri.file(fileName);
        this.disposeCallback = disposeCallback;
    }
    startCacheInterval() {
        clearInterval(this.cacheClearInterval);
        this.cacheClearInterval = setInterval(() => {
            const isOpen = vscode_1.window.visibleTextEditors.some((editor) => editor.document.uri.fsPath === this.fileName.fsPath);
            if (!isOpen) {
                errorhandler_1.ErrorHandler.logInfo(`Clearing the file "${this.fileName.fsPath}" from the internal cache`);
                this.dispose();
            }
        }, constants_1.TIME_CACHE_LIFETIME);
    }
    blame() {
        return __awaiter(this, void 0, void 0, function* () {
            return blame_1.GitBlame.blankBlameInfo();
        });
    }
    dispose() {
        clearInterval(this.cacheClearInterval);
        this.disposeCallback();
        delete this.disposeCallback;
    }
}
exports.GitFile = GitFile;
//# sourceMappingURL=file.js.map