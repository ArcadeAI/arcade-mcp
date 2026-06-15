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
const WHITESPACE = /\s/;
class EndWithDetector extends Detector_js_1.default {
    constructor(probability, ...endOfLines) {
        super(probability);
        this.endOfLines = endOfLines;
    }
    scan(line) {
        for (let i = line.length - 1; i >= 0; i--) {
            const char = line.charAt(i);
            for (const endOfLine of this.endOfLines) {
                if (char === endOfLine) {
                    return 1;
                }
            }
            if (!WHITESPACE.test(char) && char !== '*' && char !== '/') {
                return 0;
            }
        }
        return 0;
    }
}
exports.default = EndWithDetector;
