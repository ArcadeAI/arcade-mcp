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
// https://sonarsource.github.io/rspec/#/rspec/S2970/javascript
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
const ast_js_1 = require("../helpers/ast.js");
const meta = __importStar(require("./generated-meta.js"));
const assertionFunctions = [
    'a',
    'an',
    'include',
    'includes',
    'contain',
    'contains',
    'equal',
    'equals',
    'eq',
    'eql',
    'eqls',
    'above',
    'gt',
    'greaterThan',
    'least',
    'gte',
    'below',
    'lt',
    'lessThan',
    'most',
    'lte',
    'within',
    'instanceof',
    'instanceOf',
    'property',
    'ownPropertyDescriptor',
    'haveOwnPropertyDescriptor',
    'lengthOf',
    'length',
    'match',
    'matches',
    'string',
    'key',
    'keys',
    'throw',
    'throws',
    'Throw',
    'respondTo',
    'respondsTo',
    'satisfy',
    'satisfies',
    'closeTo',
    'approximately',
    'members',
    'oneOf',
    'change',
    'changes',
    'increase',
    'increases',
    'decrease',
    'decreases',
    'by',
    'fail',
];
const gettersOrModifiers = [
    'to',
    'be',
    'been',
    'is',
    'that',
    'which',
    'and',
    'has',
    'have',
    'with',
    'at',
    'of',
    'same',
    'but',
    'does',
    'still',
    // Modifier functions
    'not',
    'deep',
    'nested',
    'own',
    'ordered',
    'any',
    'all',
    'itself',
    'should',
];
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta),
    create(context) {
        return {
            ExpressionStatement(node) {
                const exprStatement = node;
                if (exprStatement.expression.type === 'MemberExpression') {
                    const { property } = exprStatement.expression;
                    if (isTestAssertion(exprStatement.expression)) {
                        if ((0, ast_js_1.isIdentifier)(property, ...assertionFunctions)) {
                            context.report({
                                node: property,
                                message: `Call this '${property.name}' assertion.`,
                            });
                        }
                        if ((0, ast_js_1.isIdentifier)(property, ...gettersOrModifiers)) {
                            context.report({
                                node: property,
                                message: `Complete this assertion; '${property.name}' doesn't assert anything by itself.`,
                            });
                        }
                    }
                }
                if (isExpectCall(exprStatement.expression)) {
                    const { callee } = exprStatement.expression;
                    context.report({
                        node: callee,
                        message: `Complete this assertion; '${callee.name}' doesn't assert anything by itself.`,
                    });
                }
            },
        };
    },
};
function isTestAssertion(node) {
    const { object, property } = node;
    // Chai's BDD style where 'should' extends Object.prototype https://www.chaijs.com/guide/styles/
    if ((0, ast_js_1.isIdentifier)(object) && (0, ast_js_1.isIdentifier)(property, 'should')) {
        return true;
    }
    if (isExpectCall(object) || (0, ast_js_1.isIdentifier)(object, 'assert', 'expect', 'should')) {
        return true;
    }
    else if (object.type === 'MemberExpression') {
        return isTestAssertion(object);
    }
    else if (object.type === 'CallExpression' && object.callee.type === 'MemberExpression') {
        return isTestAssertion(object.callee);
    }
    return false;
}
function isExpectCall(node) {
    return (node.type === 'CallExpression' &&
        (0, ast_js_1.isIdentifier)(node.callee, 'expect') &&
        !(0, ast_js_1.isNumberLiteral)(node.arguments[0]));
}
