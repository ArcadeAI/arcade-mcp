"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.MinimatchCache = void 0;
const posix_1 = require("node:path/posix");
const files_js_1 = require("../files.js");
const node_fs_1 = __importDefault(require("node:fs"));
const cache_js_1 = require("../cache.js");
exports.MinimatchCache = new cache_js_1.ComputedCache((matcher, filesystem = node_fs_1.default) => {
    return new cache_js_1.ComputedCache((from) => {
        const files = [];
        try {
            for (const entry of filesystem.readdirSync(from)) {
                const fullEntryPath = (0, files_js_1.joinPaths)(from, entry.toString());
                if (matcher.match((0, posix_1.basename)(fullEntryPath))) {
                    let stats;
                    // the resource may not be available
                    try {
                        stats = filesystem.statSync(fullEntryPath);
                    }
                    catch (error) {
                        // todo: this is testable and should be tested
                        stats = {
                            isFile: () => false,
                        };
                    }
                    if (stats.isFile()) {
                        files.push({
                            path: fullEntryPath,
                            content: filesystem.readFileSync(fullEntryPath),
                        });
                    }
                }
            }
        }
        catch { }
        return files;
    });
});
