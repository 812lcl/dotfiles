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
const valid_url_1 = require("valid-url");
const vscode_1 = require("vscode");
const constants_1 = require("../constants");
const actionablemessageitem_1 = require("../util/actionablemessageitem");
const editorvalidator_1 = require("../util/editorvalidator");
const errorhandler_1 = require("../util/errorhandler");
const execcommand_1 = require("../util/execcommand");
const gitcommand_1 = require("../util/gitcommand");
const property_1 = require("../util/property");
const textdecorator_1 = require("../util/textdecorator");
const view_1 = require("../view");
const filefactory_1 = require("./filefactory");
class GitBlame {
    constructor() {
        this.files = {};
        this.statusBarView = view_1.StatusBarView.getInstance();
        this.setupDisposables();
        this.setupListeners();
        this.init();
    }
    static blankBlameInfo() {
        return {
            commits: {},
            lines: {},
        };
    }
    static blankCommitInfo(real = false) {
        const emptyAuthor = {
            mail: "",
            name: "",
            timestamp: 0,
            tz: "",
        };
        const emptyCommitter = {
            mail: "",
            name: "",
            timestamp: 0,
            tz: "",
        };
        const commitInfo = {
            author: emptyAuthor,
            committer: emptyCommitter,
            filename: "",
            generated: true,
            hash: constants_1.HASH_NO_COMMIT_GIT,
            summary: "",
        };
        if (real) {
            delete commitInfo.generated;
        }
        return commitInfo;
    }
    static isBlankCommit(commit) {
        return commit.hash === constants_1.HASH_NO_COMMIT_GIT;
    }
    static internalHash(hash) {
        return hash.substr(0, property_1.Property.get(property_1.Properties.InternalHashLength));
    }
    blameLink() {
        return __awaiter(this, void 0, void 0, function* () {
            const commitInfo = yield this.getCommitInfo();
            const commitToolUrl = this.getToolUrl(commitInfo);
            if (commitToolUrl) {
                vscode_1.commands.executeCommand("vscode.open", commitToolUrl);
            }
            else {
                vscode_1.window.showErrorMessage("Missing gitblame.commitUrl configuration value.");
            }
        });
    }
    showMessage() {
        return __awaiter(this, void 0, void 0, function* () {
            const commitInfo = yield this.getCommitInfo();
            const messageFormat = property_1.Property.get(property_1.Properties.InfoMessageFormat);
            const normalizedTokens = textdecorator_1.TextDecorator.normalizeCommitInfoTokens(commitInfo);
            const message = textdecorator_1.TextDecorator.parseTokens(messageFormat, normalizedTokens);
            const extraActions = this.generateMessageActions(commitInfo);
            this.updateView(commitInfo);
            const actionedItem = yield vscode_1.window.showInformationMessage(message, ...(yield extraActions));
            if (actionedItem) {
                actionedItem.takeAction();
            }
        });
    }
    defaultWebPath(url, hash, isPlural) {
        return url.replace(/^(git@|https:\/\/)([^:\/]+)[:\/](.*)\.git$/, `https://$2/$3/${isPlural ? "commits" : "commit"}/${hash}`);
    }
    dispose() {
        vscode_1.Disposable.from(...Object.values(this.files)).dispose();
        this.disposable.dispose();
    }
    setupDisposables() {
        const disposables = [];
        // The blamer does not use the ErrorHandler but
        // is responsible for keeping it disposable
        const errorHandler = errorhandler_1.ErrorHandler.getInstance();
        const propertyHolder = property_1.Property.getInstance();
        this.disposable = vscode_1.Disposable.from(this.statusBarView, errorHandler, propertyHolder);
    }
    setupListeners() {
        const disposables = [];
        vscode_1.window.onDidChangeActiveTextEditor(this.onTextEditorMove, this, disposables);
        vscode_1.window.onDidChangeTextEditorSelection(this.onTextEditorMove, this, disposables);
        vscode_1.workspace.onDidSaveTextDocument(this.onTextEditorMove, this, disposables);
        this.disposable = vscode_1.Disposable.from(this.disposable, ...disposables);
    }
    init() {
        this.onTextEditorMove();
    }
    onTextEditorMove() {
        return __awaiter(this, void 0, void 0, function* () {
            const beforeBlameOpenFile = this.getCurrentActiveFileName();
            const beforeBlameLineNumber = this.getCurrentActiveLineNumber();
            const commitInfo = yield this.getCurrentLineInfo();
            // Only update if we haven't moved since we started blaming
            if (beforeBlameOpenFile === this.getCurrentActiveFileName() &&
                beforeBlameLineNumber === this.getCurrentActiveLineNumber()) {
                this.updateView(commitInfo);
            }
        });
    }
    getCurrentActiveFileName() {
        return (vscode_1.window.activeTextEditor && vscode_1.window.activeTextEditor.document.fileName);
    }
    getCurrentActiveLineNumber() {
        return (vscode_1.window.activeTextEditor &&
            vscode_1.window.activeTextEditor.selection.active.line);
    }
    generateMessageActions(commitInfo) {
        return __awaiter(this, void 0, void 0, function* () {
            const commitToolUrl = yield this.getToolUrl(commitInfo);
            const extraActions = [];
            if (commitToolUrl) {
                const viewOnlineAction = new actionablemessageitem_1.ActionableMessageItem(constants_1.TITLE_VIEW_ONLINE);
                viewOnlineAction.setAction(() => {
                    vscode_1.commands.executeCommand("vscode.open", commitToolUrl);
                });
                extraActions.push(viewOnlineAction);
            }
            return extraActions;
        });
    }
    getCommitInfo() {
        return __awaiter(this, void 0, void 0, function* () {
            const commitInfo = yield this.getCurrentLineInfo();
            if (commitInfo.generated) {
                vscode_1.window.showErrorMessage("The current file and line can not be blamed.");
            }
            return commitInfo;
        });
    }
    getToolUrl(commitInfo) {
        return __awaiter(this, void 0, void 0, function* () {
            if (GitBlame.isBlankCommit(commitInfo)) {
                return;
            }
            const parsedUrl = textdecorator_1.TextDecorator.parseTokens(property_1.Property.get(property_1.Properties.CommitUrl, "guess"), {
                hash: commitInfo.hash,
            });
            if (valid_url_1.isWebUri(parsedUrl)) {
                return vscode_1.Uri.parse(parsedUrl);
            }
            else if (parsedUrl === "guess") {
                const isWebPathPlural = property_1.Property.get(property_1.Properties.IsWebPathPlural, false);
                const origin = yield this.getOriginOfActiveFile();
                if (origin) {
                    const uri = this.defaultWebPath(origin, commitInfo.hash, isWebPathPlural);
                    return vscode_1.Uri.parse(uri);
                }
                else {
                    return;
                }
            }
            else if (parsedUrl !== "no") {
                vscode_1.window.showErrorMessage(`Malformed URL in gitblame.commitUrl. ` +
                    `Must be a valid web url, "guess", or "no".`);
            }
        });
    }
    updateView(commitInfo) {
        if (commitInfo.generated) {
            this.statusBarView.clear();
        }
        else {
            this.statusBarView.update(commitInfo);
        }
    }
    getBlameInfo(fileName) {
        return __awaiter(this, void 0, void 0, function* () {
            if (!this.files[fileName]) {
                this.files[fileName] = filefactory_1.GitFileFactory.create(fileName, this.generateDisposeFunction(fileName));
            }
            return this.files[fileName].blame();
        });
    }
    getCurrentLineInfo() {
        return __awaiter(this, void 0, void 0, function* () {
            if (editorvalidator_1.isActiveEditorValid()) {
                return this.getLineInfo(vscode_1.window.activeTextEditor.document.fileName, vscode_1.window.activeTextEditor.selection.active.line);
            }
            else {
                return GitBlame.blankCommitInfo();
            }
        });
    }
    getLineInfo(fileName, lineNumber) {
        return __awaiter(this, void 0, void 0, function* () {
            const commitLineNumber = lineNumber + 1;
            const blameInfo = yield this.getBlameInfo(fileName);
            if (blameInfo.lines[commitLineNumber]) {
                const hash = blameInfo.lines[commitLineNumber];
                return blameInfo.commits[hash];
            }
            else {
                return GitBlame.blankCommitInfo();
            }
        });
    }
    getOriginOfActiveFile() {
        return __awaiter(this, void 0, void 0, function* () {
            if (!editorvalidator_1.isActiveEditorValid()) {
                return;
            }
            const gitCommand = yield gitcommand_1.getGitCommand();
            const activeFile = vscode_1.window.activeTextEditor.document.fileName;
            const activeFileFolder = path_1.parse(activeFile).dir;
            const originUrl = yield execcommand_1.execute(gitCommand, [
                "ls-remote",
                "--get-url",
                "origin",
            ], {
                cwd: activeFileFolder,
            });
            return originUrl.trim();
        });
    }
    generateDisposeFunction(fileName) {
        return () => {
            delete this.files[fileName];
        };
    }
}
exports.GitBlame = GitBlame;
//# sourceMappingURL=blame.js.map