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
// https://sonarsource.github.io/rspec/#/rspec/S6326/javascript
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
const rule_template_js_1 = require("../helpers/regex/rule-template.js");
const range_js_1 = require("../helpers/regex/range.js");
exports.rule = (0, rule_template_js_1.createRegExpRule)(context => {
    let rawPattern;
    return {
        onRegExpLiteralEnter: (node) => {
            rawPattern = node.raw;
        },
        onCharacterEnter: (node) => {
            if (node.raw !== ' ' || node.parent.type === 'CharacterClass') {
                return;
            }
            const nextChar = rawPattern[node.start + 1];
            if (nextChar !== ' ') {
                const spacesBefore = countSpacesBefore(rawPattern, node.start);
                if (spacesBefore > 0) {
                    const spacesNumber = spacesBefore + 1;
                    const quantifier = `{${spacesNumber}}`;
                    const [start, end] = (0, range_js_1.getRegexpRange)(context.node, node);
                    const range = [start - spacesNumber + 1, end];
                    context.reportRegExpNode({
                        message: `If multiple spaces are required here, use number quantifier (${quantifier}).`,
                        regexpNode: node,
                        offset: [-spacesNumber + 1, 0],
                        node: context.node,
                        suggest: [
                            {
                                desc: `Use quantifier ${quantifier}`,
                                fix: fixer => fixer.replaceTextRange(range, ` ${quantifier}`),
                            },
                        ],
                    });
                }
            }
        },
    };
}, (0, generate_meta_js_1.generateMeta)(meta, { hasSuggestions: true }));
function countSpacesBefore(pattern, index) {
    let counter = 0;
    for (let i = index - 1; i > 0; i--) {
        if (pattern[i] === ' ') {
            counter++;
        }
        else {
            break;
        }
    }
    return counter;
}
