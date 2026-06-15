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
// https://sonarsource.github.io/rspec/#/rspec/S1192
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
const location_js_1 = require("../helpers/location.js");
const meta = __importStar(require("./generated-meta.js"));
// Number of times a literal must be duplicated to trigger an issue
const MIN_LENGTH = 10;
const NO_SEPARATOR_REGEXP = /^\w*$/;
const EXCLUDED_CONTEXTS = new Set([
    'ImportDeclaration',
    'ImportExpression',
    'JSXAttribute',
    'ExportAllDeclaration',
    'ExportNamedDeclaration',
]);
const message = 'Define a constant instead of duplicating this literal {{times}} times.';
const DEFAULT_OPTIONS = {
    threshold: 3,
    ignoreStrings: 'application/json',
};
const messages = {
    defineConstant: message,
};
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, { messages }),
    create(context) {
        const literalsByValue = new Map();
        const { threshold, ignoreStrings } = {
            ...DEFAULT_OPTIONS,
            ...context.options[0],
        };
        const whitelist = new Set(ignoreStrings.split(','));
        return {
            Literal: (node) => {
                const literal = node;
                const { parent } = literal;
                if (typeof literal.value === 'string' &&
                    parent &&
                    !['ExpressionStatement', 'TSLiteralType', 'MemberExpression'].includes(parent.type)) {
                    const stringContent = literal.value.trim();
                    if (!whitelist.has(literal.value) &&
                        !isExcludedByUsageContext(context, literal) &&
                        stringContent.length >= MIN_LENGTH &&
                        !NO_SEPARATOR_REGEXP.test(stringContent)) {
                        const sameStringLiterals = literalsByValue.get(stringContent) || [];
                        sameStringLiterals.push(literal);
                        literalsByValue.set(stringContent, sameStringLiterals);
                    }
                }
            },
            'Program:exit'() {
                for (const literals of literalsByValue.values()) {
                    if (literals.length >= threshold) {
                        const [primaryNode, ...secondaryNodes] = literals;
                        const secondaryIssues = secondaryNodes.map(node => (0, location_js_1.toSecondaryLocation)(node, 'Duplication'));
                        (0, location_js_1.report)(context, {
                            message,
                            node: primaryNode,
                            data: { times: literals.length.toString() },
                        }, secondaryIssues);
                    }
                }
            },
        };
    },
};
function isExcludedByUsageContext(context, literal) {
    const { parent } = literal;
    const parentType = parent.type;
    return (EXCLUDED_CONTEXTS.has(parentType) ||
        isRequireContext(parent, context) ||
        isObjectPropertyKey(parent, literal));
}
function isRequireContext(parent, context) {
    return (parent.type === 'CallExpression' && context.sourceCode.getText(parent.callee) === 'require');
}
function isObjectPropertyKey(parent, literal) {
    return parent.type === 'Property' && parent.key === literal;
}
