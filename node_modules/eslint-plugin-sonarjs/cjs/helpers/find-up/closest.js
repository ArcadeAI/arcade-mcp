"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.closestPatternCache = void 0;
/*
 * SonarQube JavaScript Plugin
 * Copyright (C) SonarSource Sàrl
 * mailto:info AT sonarsource DOT com
 *
 * You can redistribute and/or modify this program under the terms of
 * the Sonar Source-Available License Version 1, as published by SonarSource Sàrl.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
 * See the Sonar Source-Available License for more details.
 *
 * You should have received a copy of the Sonar Source-Available License
 * along with this program; if not, see https://sonarsource.com/license/ssal/
 */
const files_js_1 = require("../files.js");
const cache_js_1 = require("../cache.js");
const find_minimatch_js_1 = require("./find-minimatch.js");
const node_fs_1 = __importDefault(require("node:fs"));
const minimatch_1 = require("minimatch");
exports.closestPatternCache = new cache_js_1.ComputedCache((pattern, filesystem = node_fs_1.default) => {
    const matcher = new minimatch_1.Minimatch(pattern);
    const readDir = find_minimatch_js_1.MinimatchCache.get(matcher, filesystem);
    return new cache_js_1.ComputedCache((topDir) => {
        const newCache = new cache_js_1.ComputedCache((from) => {
            if (from === '.') {
                // handle path.dirname returning "." in windows
                return undefined;
            }
            const matchingFiles = readDir.get(from);
            if (matchingFiles.length > 0) {
                return matchingFiles[0];
            }
            if (!(0, files_js_1.isRoot)(from) && from !== topDir) {
                const parent = (0, files_js_1.dirnamePath)(from);
                return newCache.get(parent);
            }
            return undefined;
        });
        return newCache;
    });
});
