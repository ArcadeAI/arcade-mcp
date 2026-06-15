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
// https://sonarsource.github.io/rspec/#/rspec/S1067/javascript
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
const collection_js_1 = require("../helpers/collection.js");
const location_js_1 = require("../helpers/location.js");
const meta = __importStar(require("./generated-meta.js"));
const DEFAULT = 3;
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta),
    create(context) {
        const threshold = context.options[0]?.max ?? DEFAULT;
        const statementLevel = [new ExpressionComplexity()];
        return {
            '*': (node) => {
                const tree = node;
                if (isConditionalLike(tree)) {
                    const expr = (0, collection_js_1.last)(statementLevel);
                    expr.incrementNestedExprLevel();
                    expr.addOperator(getOperatorToken(tree, context));
                }
                else if (isScopeLike(tree)) {
                    statementLevel.push(new ExpressionComplexity());
                }
            },
            '*:exit': (node) => {
                const tree = node;
                if (isConditionalLike(tree)) {
                    const expr = (0, collection_js_1.last)(statementLevel);
                    expr.decrementNestedExprLevel();
                    if (expr.isOnFirstExprLevel()) {
                        const operators = expr.getComplexityOperators();
                        if (operators.length > threshold) {
                            reportIssue(tree, operators, threshold, context);
                        }
                        expr.resetExpressionComplexityOperators();
                    }
                }
                else if (isScopeLike(tree)) {
                    statementLevel.pop();
                }
            },
        };
    },
};
class ExpressionComplexity {
    constructor() {
        this.nestedLevel = 0;
        this.operators = [];
    }
    addOperator(operator) {
        this.operators.push(operator);
    }
    incrementNestedExprLevel() {
        this.nestedLevel++;
    }
    decrementNestedExprLevel() {
        this.nestedLevel--;
    }
    isOnFirstExprLevel() {
        return this.nestedLevel === 0;
    }
    getComplexityOperators() {
        return this.operators;
    }
    resetExpressionComplexityOperators() {
        this.operators = [];
    }
}
function isScopeLike(node) {
    return (node.type === 'FunctionExpression' ||
        (node.type === 'FunctionDeclaration' && node.generator) ||
        node.type === 'ObjectExpression' ||
        node.type === 'CallExpression' ||
        node.type === 'JSXElement');
}
function isConditionalLike(node) {
    return node.type === 'ConditionalExpression' || node.type === 'LogicalExpression';
}
function getOperatorToken(node, context) {
    const sourceCode = context.sourceCode;
    if (node.type === 'ConditionalExpression') {
        return sourceCode.getTokenAfter(node.test, token => token.type === 'Punctuator' && token.value === '?');
    }
    else {
        const expr = node;
        return sourceCode.getTokenAfter(expr.left, token => token.type === 'Punctuator' && token.value === expr.operator);
    }
}
function reportIssue(node, operators, max, context) {
    const complexity = operators.length;
    const cost = complexity - max;
    (0, location_js_1.report)(context, {
        node: node,
        message: `Reduce the number of conditional operators (${complexity}) used in the expression (maximum allowed ${max}).`,
    }, operators.map(node => (0, location_js_1.toSecondaryLocation)(node, '+1')), cost);
}
