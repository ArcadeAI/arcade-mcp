"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.patternInParentsCache = void 0;
const find_minimatch_js_1 = require("./find-minimatch.js");
const files_js_1 = require("../files.js");
const cache_js_1 = require("../cache.js");
const node_fs_1 = __importDefault(require("node:fs"));
const minimatch_1 = require("minimatch");
exports.patternInParentsCache = new cache_js_1.ComputedCache((pattern, filesystem = node_fs_1.default) => {
    const matcher = new minimatch_1.Minimatch(pattern);
    const readDir = find_minimatch_js_1.MinimatchCache.get(matcher, filesystem);
    return new cache_js_1.ComputedCache((topDir) => {
        const newCache = new cache_js_1.ComputedCache((from) => {
            if (from === '.') {
                // handle path.dirname returning "." in windows
                return [];
            }
            if (!(0, files_js_1.isRoot)(from) && from !== topDir) {
                const parent = (0, files_js_1.dirnamePath)(from);
                return [...readDir.get(from), ...newCache.get(parent)];
            }
            return [...readDir.get(from)];
        });
        return newCache;
    });
});
