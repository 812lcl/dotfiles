"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const cp = require("child_process");
const vscode = require("vscode");
const provider_1 = require("./provider");
const path = require("path");
const fs = require("fs");
var goOutlinerPath = '';
exports.envPath = process.env['PATH'] || (process.platform === 'win32' ? process.env['Path'] : null);
exports.envGoPath = process.env['GOPATH'];
class OutlineJSON {
    constructor() {
        this.label = "";
        this.type = "";
        this.receiver = "";
        this.file = "";
        this.start = 0;
        this.end = 0;
        this.line = 0;
    }
    get isTestFile() { return this.file.toLowerCase().endsWith("_test.go"); }
    static fromObject(src) {
        return Object.assign(new OutlineJSON(), src);
    }
}
exports.OutlineJSON = OutlineJSON;
class GoOutliner {
    constructor(workspaceRoot) {
        this.workspaceRoot = workspaceRoot;
        this._onDidChangeJSON = new vscode.EventEmitter();
        this.onDidChangeJSON = this._onDidChangeJSON.event;
        this.outlineJSON = Array();
        this.exludeTestFiles = true;
        this.toolPath = '';
        this.toolPath = findFromPath("go-outliner");
        this.exludeTestFiles = vscode.workspace.getConfiguration('goOutliner').get('excludeTestFiles', true);
        vscode.workspace.onDidChangeConfiguration(() => {
            this.exludeTestFiles = vscode.workspace.getConfiguration('goOutliner').get('excludeTestFiles', true);
            this._onDidChangeJSON.fire();
        });
        this.getOutlineForWorkspace();
    }
    Reload(filepath) {
        if (filepath) {
            let workPath = path.dirname(filepath);
            if (this.workspaceRoot !== workPath) {
                this.workspaceRoot = workPath;
                this.outlineJSON = Array();
                this.getOutlineForWorkspace();
            }
        }
        else {
            this.getOutlineForWorkspace();
        }
    }
    getOutlineForWorkspace() {
        if (this.toolPath === '') {
            return;
        }
        cp.execFile(this.toolPath, [`${this.workspaceRoot}`], {}, (err, stdout, stderr) => {
            this.outlineJSON = JSON.parse(stdout).map(OutlineJSON.fromObject);
            this.outlineJSON.sort((a, b) => a.label.localeCompare(b.label));
            this._onDidChangeJSON.fire();
        });
    }
    Funcs() {
        let d = this.outlineJSON.filter(x => !(this.exludeTestFiles && x.isTestFile) && x.type === "func" && !x.receiver);
        vscode.commands.executeCommand('setContext', 'showGoOutlinerFuncs', d.length > 0);
        return new provider_1.OutlineProvider(d);
    }
    Variables() {
        let d = this.outlineJSON.filter(x => !(this.exludeTestFiles && x.isTestFile) && x.type === "var" || x.type === "const");
        vscode.commands.executeCommand('setContext', 'showGoOutlinerVars', d.length > 0);
        return new provider_1.OutlineProvider(d);
    }
    Types() {
        let d = this.outlineJSON.filter(x => !(this.exludeTestFiles && x.isTestFile) && x.type === "type" || x.receiver);
        vscode.commands.executeCommand('setContext', 'showGoOutlinerTypes', d.length > 0);
        return new provider_1.OutlineProvider(d, "type");
    }
}
exports.GoOutliner = GoOutliner;
function goOutlinerInstalled() {
    if (goOutlinerPath === '') {
        goOutlinerPath = findFromPath("go-outliner");
    }
    const minVersion = "Version 0.3.0";
    return new Promise(resolve => {
        if (goOutlinerPath === '') {
            return resolve(-2);
        }
        cp.execFile(goOutlinerPath, ["-version"], {}, (err, stdout, stderr) => {
            if (err || stderr) {
                return resolve(-2);
            }
            return resolve(semver(stdout, minVersion));
        });
    });
}
exports.goOutlinerInstalled = goOutlinerInstalled;
function findFromPath(tool) {
    let toolFileName = (process.platform === 'win32') ? `${tool}.exe` : tool;
    let paths = [];
    if (exports.envPath !== undefined) {
        paths.push(...exports.envPath.split(path.delimiter));
    }
    if (exports.envGoPath !== undefined) {
        paths.push(...exports.envGoPath.split(path.delimiter));
    }
    if (process.platform === "darwin") {
        let macHome = process.env["HOME"];
        if (macHome !== undefined) {
            paths.push(path.join(macHome, "go"));
        }
    }
    for (let i = 0; i < paths.length; i++) {
        let dirs = paths[i].split(path.sep);
        let appendBin = dirs[dirs.length - 1].toLowerCase() !== "bin";
        let filePath = path.join(paths[i], appendBin ? 'bin' : '', toolFileName);
        if (fileExists(filePath)) {
            return filePath;
        }
    }
    return "";
}
function fileExists(filePath) {
    try {
        return fs.statSync(filePath).isFile();
    }
    catch (e) {
        return false;
    }
}
function installGoOutliner() {
    return new Promise(resolve => {
        cp.execFile("go", ["get", "-u", "github.com/766b/go-outliner"], {}, (err, stdout, stderr) => {
            if (err || stderr) {
                return resolve(false);
            }
            return resolve(true);
        });
    });
}
exports.installGoOutliner = installGoOutliner;
function semver(a, b) {
    a = a.split(' ')[1];
    b = b.split(' ')[1];
    var pa = a.split('.');
    var pb = b.split('.');
    for (var i = 0; i < 3; i++) {
        var na = Number(pa[i]);
        var nb = Number(pb[i]);
        if (na > nb) {
            return 1;
        }
        if (nb > na) {
            return -1;
        }
        if (!isNaN(na) && isNaN(nb)) {
            return 1;
        }
        if (isNaN(na) && !isNaN(nb)) {
            return -1;
        }
    }
    return 0;
}
//# sourceMappingURL=cmd.js.map