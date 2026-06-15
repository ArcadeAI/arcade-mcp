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
// https://sonarsource.github.io/rspec/#/rspec/S5867/javascript
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
const location_js_1 = require("../helpers/location.js");
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const meta = __importStar(require("./generated-meta.js"));
const rule_template_js_1 = require("../helpers/regex/rule-template.js");
const location_js_2 = require("../helpers/regex/location.js");
exports.rule = (0, rule_template_js_1.createRegExpRule)(context => {
    const unicodeProperties = [];
    const unicodeCharacters = [];
    let rawPattern;
    let isUnicodeEnabled = false;
    return {
        onRegExpLiteralEnter: (node) => {
            rawPattern = node.raw;
            isUnicodeEnabled = node.flags.unicode;
        },
        onQuantifierEnter: (quantifier) => {
            if (isUnicodeEnabled) {
                return;
            }
            /* \u{hhhh}, \u{hhhhh} */
            const { raw, min: hex } = quantifier;
            if (raw.startsWith(String.raw `\u`) &&
                !raw.includes(',') &&
                ['hhhh'.length, 'hhhhh'.length].includes(hex.toString().length)) {
                unicodeCharacters.push(quantifier);
            }
        },
        onCharacterEnter: (character) => {
            if (isUnicodeEnabled) {
                return;
            }
            const c = character.raw;
            if (c !== String.raw `\p` && c !== String.raw `\P`) {
                return;
            }
            let state = 'start';
            let offset = character.start + c.length;
            let nextChar;
            do {
                nextChar = rawPattern[offset];
                offset++;
                switch (state) {
                    case 'start':
                        if (nextChar === '{') {
                            state = 'openingBracket';
                        }
                        else {
                            state = 'end';
                        }
                        break;
                    case 'openingBracket':
                        if (/[a-zA-Z]/.test(nextChar)) {
                            state = 'alpha';
                        }
                        else {
                            state = 'end';
                        }
                        break;
                    case 'alpha':
                        if (/[a-zA-Z]/.test(nextChar)) {
                            state = 'alpha';
                        }
                        else if (nextChar === '=') {
                            state = 'equal';
                        }
                        else if (nextChar === '}') {
                            state = 'closingBracket';
                        }
                        else {
                            state = 'end';
                        }
                        break;
                    case 'equal':
                        if (/[a-zA-Z]/.test(nextChar)) {
                            state = 'alpha1';
                        }
                        else {
                            state = 'end';
                        }
                        break;
                    case 'alpha1':
                        if (/[a-zA-Z]/.test(nextChar)) {
                            state = 'alpha1';
                        }
                        else if (nextChar === '}') {
                            state = 'closingBracket';
                        }
                        else {
                            state = 'end';
                        }
                        break;
                    case 'closingBracket':
                        state = 'end';
                        unicodeProperties.push({ character, offset: offset - c.length - 1 });
                        break;
                }
            } while (state !== 'end');
        },
        onRegExpLiteralLeave: (regexp) => {
            if (!isUnicodeEnabled && (unicodeProperties.length > 0 || unicodeCharacters.length > 0)) {
                const secondaryLocations = [];
                for (const p of unicodeProperties) {
                    const loc = (0, location_js_2.getRegexpLocation)(context.node, p.character, context, [0, p.offset]);
                    if (loc) {
                        secondaryLocations.push((0, location_js_1.toSecondaryLocation)({ loc }, 'Unicode property'));
                    }
                }
                for (const c of unicodeCharacters) {
                    const loc = (0, location_js_2.getRegexpLocation)(context.node, c, context);
                    if (loc) {
                        secondaryLocations.push((0, location_js_1.toSecondaryLocation)({ loc }, 'Unicode character'));
                    }
                }
                context.reportRegExpNode({
                    message: `Enable the 'u' flag for this regex using Unicode constructs.`,
                    node: context.node,
                    regexpNode: regexp,
                }, secondaryLocations);
            }
        },
    };
}, (0, generate_meta_js_1.generateMeta)(meta));
