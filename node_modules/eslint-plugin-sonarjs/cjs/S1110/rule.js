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
// https://sonarsource.github.io/rspec/#/rspec/S1110/javascript
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
const ancestor_js_1 = require("../helpers/ancestor.js");
const location_js_1 = require("../helpers/location.js");
const meta = __importStar(require("./generated-meta.js"));
/**
 * Parts of the grammar that are required to have parentheses.
 */
const parenthesized = {
    DoWhileStatement: 'test',
    IfStatement: 'test',
    SwitchStatement: 'discriminant',
    WhileStatement: 'test',
    WithStatement: 'object',
    ArrowFunctionExpression: 'body',
    ImportExpression: 'source',
};
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, { hasSuggestions: true }),
    create(context) {
        return {
            '*'(node) {
                checkRedundantParentheses(context.sourceCode, node, context);
            },
        };
    },
};
function checkRedundantParentheses(sourceCode, node, context) {
    const parenthesesPairsAroundNode = getParenthesesPairsAround(sourceCode, node, node);
    const parent = (0, ancestor_js_1.getParent)(context, node);
    // Ignore parentheses pair from the parent node
    if (!!parent && isInParentNodeParentheses(node, parent)) {
        parenthesesPairsAroundNode.pop();
    }
    // One pair of parentheses is allowed for readability purposes
    parenthesesPairsAroundNode.shift();
    for (const parentheses of parenthesesPairsAroundNode) {
        (0, location_js_1.report)(context, {
            message: `Remove these redundant parentheses.`,
            loc: parentheses.openingParenthesis.loc,
            suggest: [
                {
                    desc: 'Remove these redundant parentheses',
                    fix(fixer) {
                        return [
                            fixer.remove(parentheses.openingParenthesis),
                            fixer.remove(parentheses.closingParenthesis),
                        ];
                    },
                },
            ],
        }, [(0, location_js_1.toSecondaryLocation)(parentheses.closingParenthesis)]);
    }
}
function getParenthesesPairsAround(sourceCode, start, end) {
    const tokenBefore = sourceCode.getTokenBefore(start);
    const tokenAfter = sourceCode.getTokenAfter(end);
    if (!!tokenBefore && !!tokenAfter && tokenBefore.value === '(' && tokenAfter.value === ')') {
        return [
            { openingParenthesis: tokenBefore, closingParenthesis: tokenAfter },
            ...getParenthesesPairsAround(sourceCode, tokenBefore, tokenAfter),
        ];
    }
    return [];
}
function isInParentNodeParentheses(node, parent) {
    // Applying same logic as https://github.com/eslint/eslint/blob/main/lib/rules/no-sequences.js#L81
    // both rules (S1110 and S878) can contradict each other, so better use the same logic
    const parentAttribute = parenthesized[parent.type];
    const nodeIsInConditionOfParent = parentAttribute &&
        node === parent[parentAttribute];
    const nodeIsArgumentOfCallExpression = (parent.type === 'CallExpression' || parent.type === 'NewExpression') &&
        parent.arguments.includes(node);
    return nodeIsInConditionOfParent || nodeIsArgumentOfCallExpression;
}
