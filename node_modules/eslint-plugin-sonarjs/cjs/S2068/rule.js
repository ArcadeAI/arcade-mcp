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
// https://sonarsource.github.io/rspec/#/rspec/S2068/javascript
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
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.rule = void 0;
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const ast_js_1 = require("../helpers/ast.js");
const entropy_js_1 = require("../helpers/entropy.js");
const node_path_1 = __importDefault(require("node:path"));
const meta = __importStar(require("./generated-meta.js"));
const DEFAULT_NAMES = ['password', 'pwd', 'passwd', 'passphrase'];
const ENTROPY_THRESHOLD = 3;
const MIN_PASSWORD_LENGTH = 5;
const NON_CREDENTIAL_CHARS = /[\s/["'\]<>]/;
const TEST_FILE_PATTERN = /\.(spec|test|mock)\.[jt]sx?$/;
const messages = {
    reviewPassword: 'Review this potentially hard-coded password.',
};
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, { messages }),
    create(context) {
        const filename = context.physicalFilename;
        if (TEST_FILE_PATTERN.test(filename)) {
            return {};
        }
        const dir = node_path_1.default.dirname(filename);
        const parts = dir.split(node_path_1.default.sep).map(part => part.toLowerCase());
        if (parts.includes('l10n')) {
            return {};
        }
        const variableNames = context.options[0]?.passwordWords ?? DEFAULT_NAMES;
        const lowerCaseVariableNames = variableNames.map(name => name.toLowerCase());
        const literalRegExp = lowerCaseVariableNames.map(name => new RegExp(`${name}=.+`));
        return {
            VariableDeclarator: (node) => {
                const declaration = node;
                checkAssignment(context, lowerCaseVariableNames, declaration.id, declaration.init);
            },
            AssignmentExpression: (node) => {
                const assignment = node;
                checkAssignment(context, lowerCaseVariableNames, assignment.left, assignment.right);
            },
            Property: (node) => {
                const property = node;
                checkAssignment(context, lowerCaseVariableNames, property.key, property.value);
            },
            Literal: (node) => {
                const literal = node;
                checkLiteral(context, literalRegExp, literal);
            },
            TemplateLiteral: (node) => {
                const templateLiteral = node;
                checkTemplateLiteral(context, literalRegExp, templateLiteral);
            },
            PropertyDefinition: (node) => {
                const property = node;
                checkAssignment(context, lowerCaseVariableNames, property.key, property.value);
            },
        };
    },
};
function checkAssignment(context, patterns, variable, initializer) {
    if (initializer &&
        patterns.some(pattern => context.sourceCode.getText(variable).toLowerCase().includes(pattern)) &&
        findValueSuspect(initializer)) {
        context.report({
            messageId: 'reviewPassword',
            node: initializer,
        });
    }
}
function findValueSuspect(node) {
    if (!node) {
        return false;
    }
    if ((0, ast_js_1.isStaticTemplateLiteral)(node)) {
        const value = node.quasis[0].value.cooked;
        return (value != null &&
            value.length >= MIN_PASSWORD_LENGTH &&
            !NON_CREDENTIAL_CHARS.test(value) &&
            hasHighEntropy(value));
    }
    if ((0, ast_js_1.isStringLiteral)(node)) {
        const value = node.value;
        return (value.length >= MIN_PASSWORD_LENGTH &&
            !NON_CREDENTIAL_CHARS.test(value) &&
            hasHighEntropy(value));
    }
    if (node.type === 'ConditionalExpression') {
        return findValueSuspect(node.consequent) || findValueSuspect(node.alternate);
    }
    if ((0, ast_js_1.isLogicalExpression)(node) &&
        ['??', '||'].includes(node.operator)) {
        return findValueSuspect(node.right);
    }
    return false;
}
function checkLiteral(context, patterns, literal) {
    if (!(0, ast_js_1.isStringLiteral)(literal)) {
        return;
    }
    const value = literal.value;
    checkStringValue(context, patterns, value, literal);
}
function checkTemplateLiteral(context, patterns, templateLiteral) {
    if (!(0, ast_js_1.isStaticTemplateLiteral)(templateLiteral)) {
        return;
    }
    const value = templateLiteral.quasis[0].value.cooked;
    if (value == null) {
        return;
    }
    checkStringValue(context, patterns, value, templateLiteral);
}
function checkStringValue(context, patterns, value, node) {
    const lowerValue = value.toLowerCase();
    for (const pattern of patterns) {
        const match = pattern.exec(lowerValue);
        if (!match) {
            continue;
        }
        const eqIndex = value.indexOf('=', match.index);
        if (eqIndex === -1) {
            continue;
        }
        const passwordValue = extractPasswordValue(value, eqIndex);
        if (passwordValue.length >= MIN_PASSWORD_LENGTH && hasHighEntropy(passwordValue)) {
            context.report({
                messageId: 'reviewPassword',
                node,
            });
            return;
        }
    }
}
function extractPasswordValue(value, eqIndex) {
    const passwordPart = value.substring(eqIndex + 1);
    const nextSep = findNextSeparator(passwordPart);
    return nextSep === -1 ? passwordPart : passwordPart.substring(0, nextSep);
}
function findNextSeparator(str) {
    const separators = ['&', ' ', ';'];
    let minIndex = -1;
    for (const sep of separators) {
        const idx = str.indexOf(sep);
        if (idx !== -1 && (minIndex === -1 || idx < minIndex)) {
            minIndex = idx;
        }
    }
    return minIndex;
}
function hasHighEntropy(value) {
    return (0, entropy_js_1.shannonEntropy)(value) > ENTROPY_THRESHOLD;
}
