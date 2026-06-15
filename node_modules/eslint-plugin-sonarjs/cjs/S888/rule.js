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
// https://sonarsource.github.io/rspec/#/rspec/S888/javascript
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
const allEqualityOperators = new Set(['!=', '==', '!==', '===']);
const notEqualOperators = new Set(['!==', '!=']);
const plusMinusOperators = new Set(['+=', '-=']);
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            replaceOperator: "Replace '{{operator}}' operator with one of '<=', '>=', '<', or '>' comparison operators.",
        },
    }),
    create(context) {
        return {
            ForStatement: (node) => {
                const forStatement = node;
                if (!forStatement.test || !forStatement.update) {
                    return;
                }
                const completeForStatement = node;
                const condition = completeForStatement.test;
                if (isEquality(condition) &&
                    isUpdateIncDec(completeForStatement.update) &&
                    !isException(completeForStatement, context)) {
                    context.report({
                        messageId: 'replaceOperator',
                        data: {
                            operator: condition.operator,
                        },
                        node: condition,
                    });
                }
            },
        };
    },
};
function isEquality(expression) {
    return expression.type === 'BinaryExpression' && allEqualityOperators.has(expression.operator);
}
function isUpdateIncDec(expression) {
    if (isIncDec(expression) || expression.type === 'UpdateExpression') {
        return true;
    }
    else if (expression.type === 'SequenceExpression') {
        return expression.expressions.every(isUpdateIncDec);
    }
    return false;
}
function isIncDec(expression) {
    return expression.type === 'AssignmentExpression' && plusMinusOperators.has(expression.operator);
}
function isException(forStatement, context) {
    return (isNontrivialConditionException(forStatement) ||
        isTrivialIteratorException(forStatement, context));
}
function isNontrivialConditionException(forStatement) {
    //If we reach this point, we know that test is an equality kind
    const condition = forStatement.test;
    const counters = [];
    collectCounters(forStatement.update, counters);
    return condition.left.type !== 'Identifier' || !counters.includes(condition.left.name);
}
function collectCounters(expression, counters) {
    let counter = undefined;
    if (isIncDec(expression)) {
        counter = expression.left;
    }
    else if (expression.type === 'UpdateExpression') {
        counter = expression.argument;
    }
    else if (expression.type === 'SequenceExpression') {
        for (const e of expression.expressions) {
            collectCounters(e, counters);
        }
    }
    if (counter?.type === 'Identifier') {
        counters.push(counter.name);
    }
}
function isTrivialIteratorException(forStatement, context) {
    const init = forStatement.init;
    const condition = forStatement.test;
    if (init && isNotEqual(condition)) {
        const updatedByOne = checkForUpdateByOne(forStatement.update, forStatement.body, context);
        if (updatedByOne !== 0) {
            const beginValue = getValue(init);
            const endValue = getValue(condition);
            return (beginValue !== undefined &&
                endValue !== undefined &&
                updatedByOne === Math.sign(endValue - beginValue));
        }
    }
    return false;
}
function isNotEqual(node) {
    return node.type === 'BinaryExpression' && notEqualOperators.has(node.operator);
}
function checkForUpdateByOne(update, loopBody, context) {
    if (isUpdateByOne(update, loopBody, context)) {
        if (update.operator === '++' || update.operator === '+=') {
            return +1;
        }
        if (update.operator === '--' || update.operator === '-=') {
            return -1;
        }
    }
    return 0;
}
function isUpdateByOne(update, loopBody, context) {
    return ((update.type === 'UpdateExpression' && !isUsedInsideBody(update.argument, loopBody, context)) ||
        (isUpdateOnOneWithAssign(update) && !isUsedInsideBody(update.left, loopBody, context)));
}
function isUsedInsideBody(id, loopBody, context) {
    if (id.type === 'Identifier') {
        const variable = (0, ast_js_1.getVariableFromName)(context, id.name, id);
        const bodyRange = loopBody.range;
        if (variable && bodyRange) {
            return variable.references.some(ref => isInBody(ref.identifier, bodyRange));
        }
    }
    return false;
}
function isInBody(id, bodyRange) {
    return id?.range && id.range[0] > bodyRange[0] && id.range[1] < bodyRange[1];
}
function getValue(node) {
    if (isNotEqual(node)) {
        return getInteger(node.right);
    }
    else if (isOneVarDeclaration(node)) {
        const variable = node.declarations[0];
        return getInteger(variable.init);
    }
    else if (node.type === 'AssignmentExpression') {
        return getInteger(node.right);
    }
    return undefined;
}
function getInteger(node) {
    if (node?.type === 'Literal' && typeof node.value === 'number') {
        return node.value;
    }
    return undefined;
}
function isOneVarDeclaration(node) {
    return node.type === 'VariableDeclaration' && node.declarations.length === 1;
}
function isUpdateOnOneWithAssign(expression) {
    if (isIncDec(expression)) {
        const right = expression.right;
        return right.type === 'Literal' && right.value === 1;
    }
    return false;
}
