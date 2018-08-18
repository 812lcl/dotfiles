"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
class GitPlatformDetector {
    static defaultPath(url, hash) {
        return url.replace(/^(git@|https:\/\/)([^:\/]+)[:\/](.*)\.git$/, `https://$2/$3/commit/${hash}`);
    }
}
exports.GitPlatformDetector = GitPlatformDetector;
//# sourceMappingURL=gitplatformdetector.js.map