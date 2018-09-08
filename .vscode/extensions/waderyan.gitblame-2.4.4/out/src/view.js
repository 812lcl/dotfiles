"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const vscode_1 = require("vscode");
const blame_1 = require("./git/blame");
const property_1 = require("./util/property");
const spinner_1 = require("./util/spinner");
const textdecorator_1 = require("./util/textdecorator");
class StatusBarView {
    constructor() {
        this.spinnerActive = false;
        this.statusBarItem = vscode_1.window.createStatusBarItem(vscode_1.StatusBarAlignment.Left, property_1.Property.get(property_1.Properties.StatusBarPositionPriority));
        this.spinner = new spinner_1.Spinner();
    }
    static getInstance() {
        if (!this.instance) {
            this.instance = new StatusBarView();
        }
        return this.instance;
    }
    clear() {
        this.stopProgress();
        this.setText("", false);
    }
    update(commitInfo) {
        this.stopProgress();
        if (commitInfo && !commitInfo.generated) {
            const clickable = !blame_1.GitBlame.isBlankCommit(commitInfo);
            this.setText(textdecorator_1.TextDecorator.toTextView(commitInfo), clickable);
        }
        else {
            this.clear();
        }
    }
    stopProgress() {
        clearInterval(this.progressInterval);
        this.spinnerActive = false;
    }
    startProgress() {
        if (this.spinnerActive) {
            return;
        }
        this.stopProgress();
        if (this.spinner.updatable()) {
            this.progressInterval = setInterval(() => {
                this.setSpinner();
            }, 100);
        }
        else {
            this.setSpinner();
        }
        this.spinnerActive = true;
    }
    dispose() {
        this.stopProgress();
        this.statusBarItem.dispose();
    }
    setText(text, hasCommand = true) {
        this.statusBarItem.text = text
            ? `$(git-commit) ${text}`
            : "$(git-commit)";
        this.statusBarItem.tooltip = hasCommand
            ? "git blame"
            : "git blame - No info about the current line";
        this.statusBarItem.command = hasCommand ? "gitblame.quickInfo" : "";
        this.statusBarItem.show();
    }
    setSpinner() {
        this.setText(`${this.spinner} Waiting for git blame response`, false);
    }
}
exports.StatusBarView = StatusBarView;
//# sourceMappingURL=view.js.map