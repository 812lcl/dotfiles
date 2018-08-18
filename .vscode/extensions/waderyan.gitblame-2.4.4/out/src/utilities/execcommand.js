"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const child_process_1 = require("child_process");
const errorhandler_1 = require("util/errorhandler");
function execute(command, args, options = {}) {
    return new Promise((resolve, reject) => {
        errorhandler_1.ErrorHandler.logCommand(`${command} ${args.join(" ")}`);
        child_process_1.execFile(command, args, options, (error, stdout, stderr) => {
            if (error) {
                errorhandler_1.ErrorHandler.logError(new Error(stderr));
                resolve("");
            }
            else {
                resolve(stdout);
            }
        });
    });
}
exports.execute = execute;
//# sourceMappingURL=execcommand.js.map