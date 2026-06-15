"use strict";
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
// https://sonarsource.github.io/rspec/#/rspec/S1451/javascript
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.rule = void 0;
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const meta = __importStar(require("./generated-meta.js"));
let cached;
const DEFAULT_OPTIONS = {
    headerFormat: '',
    isRegularExpression: false,
};
const messages = {
    fixHeader: 'Add or update the header of this file.',
};
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, { messages }),
    create(context) {
        updateCache(context.options);
        if (cached.failedToCompile) {
            // don't visit anything
            return {};
        }
        return {
            'Program:exit'() {
                if (cached.isRegularExpression) {
                    checkRegularExpression(cached.searchPattern, context);
                }
                else {
                    checkPlainText(cached.expectedLines, context);
                }
            },
        };
    },
};
function checkPlainText(expectedLines, context) {
    let matches = false;
    const lines = context.sourceCode.lines;
    if (expectedLines.length <= lines.length) {
        matches = true;
        let i = 0;
        for (const expectedLine of expectedLines) {
            const line = lines[i];
            i++;
            if (line !== expectedLine) {
                matches = false;
                break;
            }
        }
    }
    if (!matches) {
        addFileIssue(context);
    }
}
function checkRegularExpression(searchPattern, context) {
    const fileContent = context.sourceCode.getText();
    const match = searchPattern.exec(fileContent);
    if (match?.index !== 0) {
        addFileIssue(context);
    }
}
function addFileIssue(context) {
    context.report({
        messageId: 'fixHeader',
        loc: { line: 0, column: 0 },
    });
}
function updateCache(options) {
    const { headerFormat, isRegularExpression } = {
        ...DEFAULT_OPTIONS,
        ...options[0],
    };
    if (!cached ||
        cached.headerFormat !== headerFormat ||
        cached.isRegularExpression !== isRegularExpression) {
        cached = {
            headerFormat,
            isRegularExpression,
        };
        if (isRegularExpression) {
            try {
                cached.searchPattern = new RegExp(headerFormat, 's');
                cached.failedToCompile = false;
            }
            catch (e) {
                console.error(`Failed to compile regular expression for rule S1451 (${e.message})`);
                cached.failedToCompile = true;
            }
        }
        else {
            cached.expectedLines = headerFormat.split(/(?:\r)?\n|\r/);
        }
    }
}
