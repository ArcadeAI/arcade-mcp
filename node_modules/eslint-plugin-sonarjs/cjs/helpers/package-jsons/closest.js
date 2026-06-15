"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.getClosestPackageJSONDir = getClosestPackageJSONDir;
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
const index_js_1 = require("./index.js");
const closest_js_1 = require("../find-up/closest.js");
function getClosestPackageJSONDir(dir, topDir) {
    const closestPackageJSONDir = closest_js_1.closestPatternCache
        .get(index_js_1.PACKAGE_JSON)
        .get(topDir ?? files_js_1.ROOT_PATH)
        .get(dir)?.path;
    if (closestPackageJSONDir) {
        return (0, files_js_1.dirnamePath)(closestPackageJSONDir);
    }
    return undefined;
}
