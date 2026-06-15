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
// https://sonarsource.github.io/rspec/#/rspec/S6353/javascript
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
exports.rule = (0, rule_template_js_1.createRegExpRule)(context => {
    let flags;
    return {
        onRegExpLiteralEnter: (node) => {
            ({ flags } = node);
        },
        onCharacterClassEnter: (node) => {
            checkBulkyAnyCharacterClass(node, flags, context);
            checkBulkyNumericCharacterClass(node, context);
            checkBulkyAlphaNumericCharacterClass(node, context);
        },
        onQuantifierEnter: (node) => {
            checkBulkyQuantifier(node, context);
        },
    };
}, (0, generate_meta_js_1.generateMeta)(meta));
function checkBulkyAnyCharacterClass(node, flags, context) {
    if (node.negate || node.elements.length !== 2) {
        return;
    }
    let hasLowerEscapeW = false;
    let hasUpperEscapeW = false;
    let hasLowerEscapeD = false;
    let hasUpperEscapeD = false;
    let hasLowerEscapeS = false;
    let hasUpperEscapeS = false;
    for (const element of node.elements) {
        hasLowerEscapeW ||=
            element.type === 'CharacterSet' && element.kind === 'word' && !element.negate;
        hasUpperEscapeW ||=
            element.type === 'CharacterSet' && element.kind === 'word' && element.negate;
        hasLowerEscapeD ||=
            element.type === 'CharacterSet' && element.kind === 'digit' && !element.negate;
        hasUpperEscapeD ||=
            element.type === 'CharacterSet' && element.kind === 'digit' && element.negate;
        hasLowerEscapeS ||=
            element.type === 'CharacterSet' && element.kind === 'space' && !element.negate;
        hasUpperEscapeS ||=
            element.type === 'CharacterSet' && element.kind === 'space' && element.negate;
    }
    const isBulkyAnyCharacterClass = (hasLowerEscapeW && hasUpperEscapeW) ||
        (hasLowerEscapeD && hasUpperEscapeD) ||
        (hasLowerEscapeS && hasUpperEscapeS && flags.dotAll);
    if (isBulkyAnyCharacterClass) {
        context.reportRegExpNode({
            message: `Use concise character class syntax '.' instead of '${node.raw}'.`,
            node: context.node,
            regexpNode: node,
        });
    }
}
function checkBulkyNumericCharacterClass(node, context) {
    if (node.elements.length === 1) {
        const [element] = node.elements;
        const hasDigit = element.type === 'CharacterClassRange' && element.raw === '0-9';
        if (hasDigit) {
            const expected = node.negate ? String.raw `\D` : String.raw `\d`;
            const actual = node.raw;
            context.reportRegExpNode({
                message: `Use concise character class syntax '${expected}' instead of '${actual}'.`,
                node: context.node,
                regexpNode: node,
            });
        }
    }
}
function checkBulkyAlphaNumericCharacterClass(node, context) {
    if (node.elements.length === 4) {
        let hasDigit = false, hasLowerCase = false, hasUpperCase = false, hasUnderscore = false;
        for (const element of node.elements) {
            hasDigit ||= element.type === 'CharacterClassRange' && element.raw === '0-9';
            hasLowerCase ||= element.type === 'CharacterClassRange' && element.raw === 'a-z';
            hasUpperCase ||= element.type === 'CharacterClassRange' && element.raw === 'A-Z';
            hasUnderscore ||= element.type === 'Character' && element.raw === '_';
        }
        if (hasDigit && hasLowerCase && hasUpperCase && hasUnderscore) {
            const expected = node.negate ? String.raw `\W` : String.raw `\w`;
            const actual = node.raw;
            context.reportRegExpNode({
                message: `Use concise character class syntax '${expected}' instead of '${actual}'.`,
                node: context.node,
                regexpNode: node,
            });
        }
    }
}
function checkBulkyQuantifier(node, context) {
    const { raw } = node;
    let message;
    let bulkyQuantifier;
    if (/\{0,1\}\??$/.test(raw)) {
        bulkyQuantifier = { concise: '?', verbose: '{0,1}' };
    }
    else if (/\{0,0\}\??$/.test(raw)) {
        message = `Remove redundant ${node.element.raw}{0,0}.`;
    }
    else if (/\{0\}\??$/.test(raw)) {
        message = `Remove redundant ${node.element.raw}{0}.`;
    }
    else if (/\{1,1\}\??$/.test(raw)) {
        message = 'Remove redundant quantifier {1,1}.';
    }
    else if (/\{1\}\??$/.test(raw)) {
        message = 'Remove redundant quantifier {1}.';
    }
    else if (/\{0,\}\??$/.test(raw)) {
        bulkyQuantifier = { concise: '*', verbose: '{0,}' };
    }
    else if (/\{1,\}\??$/.test(raw)) {
        bulkyQuantifier = { concise: '+', verbose: '{1,}' };
    }
    else if (/\{(\d+),\1\}\??$/.test(raw)) {
        bulkyQuantifier = { concise: `{${node.min}}`, verbose: `{${node.min},${node.min}}` };
    }
    if (bulkyQuantifier) {
        message = `Use concise quantifier syntax '${bulkyQuantifier.concise}' instead of '${bulkyQuantifier.verbose}'.`;
    }
    if (message) {
        context.reportRegExpNode({
            message,
            node: context.node,
            regexpNode: node,
        });
    }
}
