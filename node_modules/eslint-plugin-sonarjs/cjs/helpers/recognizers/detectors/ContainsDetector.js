"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
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
const Detector_js_1 = __importDefault(require("../Detector.js"));
class ContainsDetector extends Detector_js_1.default {
    constructor(probability, ...strings) {
        super(probability);
        this.patterns = strings.map(str => typeof str === 'string' ? new RegExp(escapeRegex(str), 'g') : str);
    }
    scan(line) {
        const lineWithoutSpaces = line.replace(/\s+/, '');
        let matchers = 0;
        for (const pattern of this.patterns) {
            matchers += (lineWithoutSpaces.match(pattern) ?? []).length;
        }
        return matchers;
    }
}
exports.default = ContainsDetector;
function escapeRegex(value) {
    return value.replaceAll(/[-/\\^$*+?.()|[\]{}]/g, String.raw `\$&`);
}
