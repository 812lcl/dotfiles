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
const path_1 = require("path");
const vscode_1 = require("vscode");
const errorhandler_1 = require("../util/errorhandler");
const execcommand_1 = require("../util/execcommand");
const gitcommand_1 = require("../util/gitcommand");
const view_1 = require("../view");
const blame_1 = require("./blame");
const file_1 = require("./file");
const stream_1 = require("./stream");
class GitFilePhysical extends file_1.GitFile {
    constructor(fileName, disposeCallback) {
        super(fileName, disposeCallback);
        this.fileSystemWatcher = this.setupWatcher();
    }
    blame() {
        return __awaiter(this, void 0, void 0, function* () {
            view_1.StatusBarView.getInstance().startProgress();
            if (this.blameInfoPromise) {
                return this.blameInfoPromise;
            }
            else {
                return this.findBlameInfo();
            }
        });
    }
    dispose() {
        super.dispose();
        if (this.blameProcess) {
            this.blameProcess.terminate();
            delete this.blameProcess;
        }
        this.fileSystemWatcher.dispose();
    }
    setupWatcher() {
        const relativePath = vscode_1.workspace.asRelativePath(this.fileName);
        const fsWatcher = vscode_1.workspace.createFileSystemWatcher(relativePath, true, false, false);
        fsWatcher.onDidChange(() => {
            this.changed();
        });
        fsWatcher.onDidDelete(() => {
            this.dispose();
        });
        return fsWatcher;
    }
    changed() {
        delete this.workTree;
        delete this.blameInfoPromise;
    }
    getGitWorkTree() {
        return __awaiter(this, void 0, void 0, function* () {
            if (this.workTree) {
                return this.workTree;
            }
            if (!this.workTreePromise) {
                this.workTreePromise = this.findWorkTree();
            }
            this.workTree = yield this.workTreePromise;
            return this.workTree;
        });
    }
    findWorkTree() {
        return __awaiter(this, void 0, void 0, function* () {
            const workTree = yield this.executeGitRevParseCommand("--show-toplevel");
            if (workTree === "") {
                return "";
            }
            else {
                return path_1.normalize(workTree);
            }
        });
    }
    executeGitRevParseCommand(command) {
        return __awaiter(this, void 0, void 0, function* () {
            const currentDirectory = path_1.dirname(this.fileName.fsPath);
            const gitCommand = yield gitcommand_1.getGitCommand();
            const gitExecArguments = ["rev-parse", command];
            const gitExecOptions = {
                cwd: currentDirectory,
            };
            const gitRev = yield execcommand_1.execute(gitCommand, gitExecArguments, gitExecOptions);
            return gitRev.trim();
        });
    }
    findBlameInfo() {
        return __awaiter(this, void 0, void 0, function* () {
            const workTree = yield this.getGitWorkTree();
            const blameInfo = blame_1.GitBlame.blankBlameInfo();
            if (workTree) {
                this.blameInfoPromise = new Promise((resolve, reject) => {
                    this.blameProcess = new stream_1.GitBlameStream(this.fileName, workTree);
                    this.blameProcess.on("commit", this.gitAddCommit(blameInfo));
                    this.blameProcess.on("line", this.gitAddLine(blameInfo));
                    this.blameProcess.on("end", this.gitStreamOver(this.blameProcess, reject, resolve, blameInfo));
                });
            }
            else {
                view_1.StatusBarView.getInstance().stopProgress();
                this.startCacheInterval();
                errorhandler_1.ErrorHandler.logInfo(`File "${this.fileName.fsPath}" is not a decendant of a git repository`);
                this.blameInfoPromise = Promise.resolve(blameInfo);
            }
            return this.blameInfoPromise;
        });
    }
    gitAddCommit(blameInfo) {
        return (internalHash, data) => {
            blameInfo.commits[internalHash] = data;
        };
    }
    gitAddLine(blameInfo) {
        return (line, gitCommitHash) => {
            blameInfo.lines[line] = gitCommitHash;
        };
    }
    gitStreamOver(gitStream, reject, resolve, blameInfo) {
        return (err) => {
            gitStream.removeAllListeners();
            view_1.StatusBarView.getInstance().stopProgress();
            this.startCacheInterval();
            if (err) {
                errorhandler_1.ErrorHandler.logError(err);
                resolve(blame_1.GitBlame.blankBlameInfo());
            }
            else {
                errorhandler_1.ErrorHandler.logInfo(`Blamed file "${this.fileName.fsPath}" and found ${Object.keys(blameInfo.commits).length} commits`);
                resolve(blameInfo);
            }
        };
    }
}
exports.GitFilePhysical = GitFilePhysical;
//# sourceMappingURL=filephysical.js.map