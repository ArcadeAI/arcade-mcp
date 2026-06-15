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
// https://sonarsource.github.io/rspec/#/rspec/S2589
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
const location_js_1 = require("../helpers/location.js");
const meta = __importStar(require("./generated-meta.js"));
const message = 'This always evaluates to {{value}}. Consider refactoring this code.';
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            refactorBooleanExpression: message,
        },
    }),
    create(context) {
        const truthyMap = new Map();
        const falsyMap = new Map();
        function isInsideJSX(node) {
            const ancestors = context.sourceCode.getAncestors(node);
            return ancestors.some(ancestor => ancestor.type === 'JSXExpressionContainer');
        }
        return {
            IfStatement: (node) => {
                const { test } = node;
                if (test.type === 'Literal' && typeof test.value === 'boolean') {
                    reportIssue(test, undefined, context, test.value);
                }
            },
            ':statement': (node) => {
                const { parent } = node;
                if ((0, ast_js_1.isIfStatement)(parent)) {
                    // we visit 'consequent' and 'alternate' and not if-statement directly in order to get scope for 'consequent'
                    const currentScope = context.sourceCode.getScope(node);
                    if (parent.consequent === node) {
                        const { truthy, falsy } = collectKnownIdentifiers(parent.test);
                        truthyMap.set(parent.consequent, transformAndFilter(truthy, currentScope));
                        falsyMap.set(parent.consequent, transformAndFilter(falsy, currentScope));
                    }
                    else if (parent.alternate === node && (0, ast_js_1.isIdentifier)(parent.test)) {
                        falsyMap.set(parent.alternate, transformAndFilter([parent.test], currentScope));
                    }
                }
            },
            ':statement:exit': (node) => {
                const stmt = node;
                truthyMap.delete(stmt);
                falsyMap.delete(stmt);
            },
            Identifier: (node) => {
                const id = node;
                const symbol = getSymbol(id, context.sourceCode.getScope(node));
                const { parent } = node;
                if (!symbol || !parent || (isInsideJSX(node) && isLogicalAndRhs(id, parent))) {
                    return;
                }
                if (!isLogicalAnd(parent) &&
                    !isLogicalOrLhs(id, parent) &&
                    !(0, ast_js_1.isIfStatement)(parent) &&
                    !isLogicalNegation(parent)) {
                    return;
                }
                const checkIfKnownAndReport = (map, truthy) => {
                    for (const references of map.values()) {
                        const ref = references.find(ref => ref.resolved === symbol);
                        if (ref) {
                            reportIssue(id, ref, context, truthy);
                        }
                    }
                };
                checkIfKnownAndReport(truthyMap, true);
                checkIfKnownAndReport(falsyMap, false);
            },
            Program: () => {
                truthyMap.clear();
                falsyMap.clear();
            },
        };
    },
};
function collectKnownIdentifiers(expression) {
    const truthy = [];
    const falsy = [];
    const checkExpr = (expr) => {
        if ((0, ast_js_1.isIdentifier)(expr)) {
            truthy.push(expr);
        }
        else if (isLogicalNegation(expr)) {
            if ((0, ast_js_1.isIdentifier)(expr.argument)) {
                falsy.push(expr.argument);
            }
            else if (isLogicalNegation(expr.argument) && (0, ast_js_1.isIdentifier)(expr.argument.argument)) {
                truthy.push(expr.argument.argument);
            }
        }
    };
    let current = expression;
    checkExpr(current);
    while (isLogicalAnd(current)) {
        checkExpr(current.right);
        current = current.left;
    }
    checkExpr(current);
    return { truthy, falsy };
}
function isLogicalAnd(expression) {
    return expression.type === 'LogicalExpression' && expression.operator === '&&';
}
function isLogicalOrLhs(id, expression) {
    return (expression.type === 'LogicalExpression' &&
        expression.operator === '||' &&
        expression.left === id);
}
function isLogicalAndRhs(id, expression) {
    return (expression.parent?.type !== 'LogicalExpression' &&
        expression.type === 'LogicalExpression' &&
        expression.operator === '&&' &&
        expression.right === id);
}
function isLogicalNegation(expression) {
    return expression.type === 'UnaryExpression' && expression.operator === '!';
}
function isDefined(x) {
    return x != null;
}
function getSymbol(id, scope) {
    const ref = scope.references.find(r => r.identifier === id);
    if (ref) {
        return ref.resolved;
    }
    return null;
}
function getFunctionScope(scope) {
    if (scope.type === 'function') {
        return scope;
    }
    else if (!scope.upper) {
        return null;
    }
    return getFunctionScope(scope.upper);
}
function mightBeWritten(symbol, currentScope) {
    return symbol.references
        .filter(ref => ref.isWrite())
        .find(ref => {
        const refScope = ref.from;
        let cur = refScope;
        while (cur) {
            if (cur === currentScope) {
                return true;
            }
            cur = cur.upper;
        }
        const currentFunc = getFunctionScope(currentScope);
        const refFunc = getFunctionScope(refScope);
        return refFunc !== currentFunc;
    });
}
function transformAndFilter(ids, currentScope) {
    return ids
        .map(id => currentScope.upper?.references.find(r => r.identifier === id))
        .filter(isDefined)
        .filter(ref => isDefined(ref.resolved))
        .filter(ref => !mightBeWritten(ref.resolved, currentScope));
}
function reportIssue(id, ref, context, truthy) {
    const value = truthy ? 'truthy' : 'falsy';
    (0, location_js_1.report)(context, {
        message,
        data: {
            value,
        },
        node: id,
    }, ref?.identifier ? [(0, location_js_1.toSecondaryLocation)(ref.identifier, `Evaluated here to be ${value}`)] : []);
}
