'use strict';
Object.defineProperty(exports, "__esModule", { value: true });
const fs = require("fs");
function semVer(a, b) {
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
exports.semVer = semVer;
function fileExists(filePath) {
    try {
        return fs.statSync(filePath).isFile();
    }
    catch (e) {
        return false;
    }
}
exports.fileExists = fileExists;
//# sourceMappingURL=util.js.map