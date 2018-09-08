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
const constants_1 = require("@/constants");
const property_1 = require("util/property");
var LogCategory;
(function (LogCategory) {
    LogCategory["Info"] = "info";
    LogCategory["Error"] = "error";
    LogCategory["Command"] = "command";
    LogCategory["Critical"] = "critical";
})(LogCategory || (LogCategory = {}));
class ErrorHandler {
    static logInfo(message) {
        ErrorHandler.getInstance().writeToLog(LogCategory.Info, message);
    }
    static logCommand(message) {
        ErrorHandler.getInstance().writeToLog(LogCategory.Command, message);
    }
    static logError(error) {
        ErrorHandler.getInstance().writeToLog(LogCategory.Error, error.toString());
    }
    static logCritical(error, message) {
        ErrorHandler.getInstance().writeToLog(LogCategory.Critical, error.toString());
        ErrorHandler.getInstance().showErrorMessage(message);
    }
    static getInstance() {
        if (!ErrorHandler.instance) {
            ErrorHandler.instance = new ErrorHandler();
        }
        return ErrorHandler.instance;
    }
    static timestamp() {
        const now = new Date();
        const hour = now
            .getHours()
            .toString()
            .padStart(2, "0");
        const minute = now
            .getMinutes()
            .toString()
            .padStart(2, "0");
        const second = now
            .getSeconds()
            .toString()
            .padStart(2, "0");
        return `${hour}:${minute}:${second}`;
    }
    constructor() {
        this.outputChannel = vscode_1.window.createOutputChannel("Extension: gitblame");
    }
    dispose() {
        this.outputChannel.dispose();
    }
    showErrorMessage(message) {
        return __awaiter(this, void 0, void 0, function* () {
            const selectedItem = yield vscode_1.window.showErrorMessage(message, constants_1.TITLE_SHOW_LOG);
            if (selectedItem === constants_1.TITLE_SHOW_LOG) {
                this.outputChannel.show();
            }
        });
    }
    writeToLog(category, message) {
        const allowCategory = this.logCategoryAllowed(category);
        if (allowCategory) {
            const trimmedMessage = message.trim();
            const timestamp = ErrorHandler.timestamp();
            this.outputChannel.appendLine(`[ ${timestamp} | ${category} ] ${trimmedMessage}`);
        }
        return allowCategory;
    }
    logCategoryAllowed(level) {
        const enabledLevels = property_1.Property.get(property_1.Properties.LogLevel, []);
        return enabledLevels.includes(level);
    }
}
exports.ErrorHandler = ErrorHandler;
//# sourceMappingURL=errorhandler.js.map