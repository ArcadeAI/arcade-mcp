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
// https://sonarsource.github.io/rspec/#/rspec/S3516/javascript
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
const ancestor_js_1 = require("../helpers/ancestor.js");
const ast_js_1 = require("../helpers/ast.js");
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const location_js_1 = require("../helpers/location.js");
const meta = __importStar(require("./generated-meta.js"));
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta),
    create(context) {
        const functionContextStack = [];
        const codePathSegments = [];
        let currentCodePathSegments = [];
        const checkOnFunctionExit = (node) => checkInvariantReturnStatements(node, functionContextStack.at(-1));
        function checkInvariantReturnStatements(node, functionContext) {
            if (!functionContext || hasDifferentReturnTypes(functionContext, currentCodePathSegments)) {
                return;
            }
            const returnedValues = functionContext.returnStatements.map(returnStatement => returnStatement.argument);
            if (areAllSameValue(returnedValues, context.sourceCode.getScope(node))) {
                const firstValue = getLiteralValue(returnedValues[0], context.sourceCode.getScope(node));
                if (firstValue === undefined && functionContext.hasSideEffectOnlyBranch) {
                    return;
                }
                // Suppress literal invariant returns only when ALL branching returns are accompanied
                // by side effects (no pure-return branches exist). This distinguishes intentional
                // control flow (every branch does real work before returning the same literal) from
                // dead code (some branch returns the literal with no side effect).
                if (firstValue !== undefined &&
                    functionContext.hasSideEffectBranchWithReturn &&
                    !functionContext.hasReturnBranchWithoutSideEffect) {
                    return;
                }
                (0, location_js_1.report)(context, {
                    message: `Refactor this function to not always return the same value.`,
                    loc: (0, location_js_1.getMainFunctionTokenLocation)(node, (0, ancestor_js_1.getParent)(context, node), context),
                }, returnedValues.map(node => (0, location_js_1.toSecondaryLocation)(node, 'Returned value.')), returnedValues.length);
            }
        }
        function pushBranchFrame() {
            functionContextStack.at(-1)?.branchStack.push({ hasSideEffect: false, hasReturn: false });
        }
        function popBranchFrame() {
            const ctx = functionContextStack.at(-1);
            if (ctx) {
                const frame = ctx.branchStack.pop();
                if (frame?.hasSideEffect && !frame.hasReturn) {
                    ctx.hasSideEffectOnlyBranch = true;
                }
                if (frame?.hasSideEffect && frame.hasReturn) {
                    ctx.hasSideEffectBranchWithReturn = true;
                }
                if (frame?.hasReturn && !frame.hasSideEffect) {
                    ctx.hasReturnBranchWithoutSideEffect = true;
                }
            }
        }
        function recordSideEffect(node) {
            const ctx = functionContextStack.at(-1);
            if (!ctx) {
                return;
            }
            const frame = ctx.branchStack.at(-1);
            if (frame) {
                frame.hasSideEffect = true;
            }
            // Also handle bare statement branches where ExpressionStatement IS the branch body
            // (e.g. `if (x) doSomething()` — no BlockStatement is pushed for such a branch)
            const exprStmt = node.parent;
            if (exprStmt && isBranchBody(exprStmt)) {
                ctx.hasSideEffectOnlyBranch = true;
            }
        }
        return {
            onCodePathStart(codePath) {
                functionContextStack.push({
                    codePath,
                    containsReturnWithoutValue: false,
                    returnStatements: [],
                    branchStack: [],
                    hasSideEffectOnlyBranch: false,
                    hasSideEffectBranchWithReturn: false,
                    hasReturnBranchWithoutSideEffect: false,
                });
                codePathSegments.push(currentCodePathSegments);
                currentCodePathSegments = [];
            },
            onCodePathEnd() {
                functionContextStack.pop();
                currentCodePathSegments = codePathSegments.pop() || [];
            },
            onCodePathSegmentStart: (segment) => {
                currentCodePathSegments.push(segment);
            },
            onCodePathSegmentEnd() {
                currentCodePathSegments.pop();
            },
            ReturnStatement(node) {
                const currentContext = functionContextStack.at(-1);
                if (currentContext) {
                    const returnStatement = node;
                    currentContext.containsReturnWithoutValue =
                        currentContext.containsReturnWithoutValue || !returnStatement.argument;
                    currentContext.returnStatements.push(returnStatement);
                    const frame = currentContext.branchStack.at(-1);
                    if (frame) {
                        frame.hasReturn = true;
                    }
                }
            },
            BlockStatement(node) {
                if (isBranchBody(node)) {
                    pushBranchFrame();
                }
            },
            'BlockStatement:exit'(node) {
                if (isBranchBody(node)) {
                    popBranchFrame();
                }
            },
            SwitchCase() {
                pushBranchFrame();
            },
            'SwitchCase:exit'() {
                popBranchFrame();
            },
            'ExpressionStatement > CallExpression'(node) {
                recordSideEffect(node);
            },
            'ExpressionStatement > AssignmentExpression'(node) {
                recordSideEffect(node);
            },
            'FunctionDeclaration:exit': checkOnFunctionExit,
            'FunctionExpression:exit': checkOnFunctionExit,
            'ArrowFunctionExpression:exit': checkOnFunctionExit,
        };
    },
};
function hasDifferentReturnTypes(functionContext, currentSegments) {
    // As this method is called at the exit point of a function definition, the current
    // segments are the ones leading to the exit point at the end of the function. If they
    // are reachable, it means there is an implicit return.
    const hasImplicitReturn = currentSegments.some(segment => segment.reachable);
    return (hasImplicitReturn ||
        functionContext.containsReturnWithoutValue ||
        functionContext.returnStatements.length <= 1 ||
        functionContext.codePath.thrownSegments.length > 0);
}
function areAllSameValue(returnedValues, scope) {
    const firstReturnedValue = returnedValues[0];
    const firstValue = getLiteralValue(firstReturnedValue, scope);
    if (firstValue !== undefined) {
        return returnedValues
            .slice(1)
            .every(returnedValue => getLiteralValue(returnedValue, scope) === firstValue);
    }
    else if (firstReturnedValue.type === 'Identifier') {
        const singleWriteVariable = getSingleWriteDefinition(firstReturnedValue.name, scope);
        if (singleWriteVariable) {
            const readReferenceIdentifiers = new Set(singleWriteVariable.variable.references.slice(1).map(ref => ref.identifier));
            return returnedValues.every(returnedValue => readReferenceIdentifiers.has(returnedValue));
        }
    }
    return false;
}
function getSingleWriteDefinition(variableName, scope) {
    const variable = scope.set.get(variableName);
    if (variable) {
        const references = variable.references.slice(1);
        if (!references.some(ref => ref.isWrite() || isPossibleObjectUpdate(ref))) {
            let initExpression = null;
            if (variable.defs.length === 1 && variable.defs[0].type === 'Variable') {
                initExpression = variable.defs[0].node.init;
            }
            return { variable, initExpression };
        }
    }
    return null;
}
function isPossibleObjectUpdate(ref) {
    const expressionStatement = (0, ancestor_js_1.findFirstMatchingAncestor)(ref.identifier, n => n.type === 'ExpressionStatement' || ast_js_1.FUNCTION_NODES.includes(n.type));
    // To avoid FP, we consider method calls as write operations, since we do not know whether they will
    // update the object state or not.
    return (expressionStatement?.type === 'ExpressionStatement' &&
        ((0, ast_js_1.isElementWrite)(expressionStatement, ref) ||
            expressionStatement.expression.type === 'CallExpression'));
}
function getLiteralValue(returnedValue, scope) {
    if (returnedValue.type === 'Literal') {
        return returnedValue.value;
    }
    else if (returnedValue.type === 'UnaryExpression') {
        const innerReturnedValue = getLiteralValue(returnedValue.argument, scope);
        return innerReturnedValue === undefined
            ? undefined
            : evaluateUnaryLiteralExpression(returnedValue.operator, innerReturnedValue);
    }
    else if (returnedValue.type === 'Identifier') {
        const singleWriteVariable = getSingleWriteDefinition(returnedValue.name, scope);
        if (singleWriteVariable?.initExpression) {
            return getLiteralValue(singleWriteVariable.initExpression, scope);
        }
    }
    return undefined;
}
function evaluateUnaryLiteralExpression(operator, innerReturnedValue) {
    switch (operator) {
        case '-':
            return -Number(innerReturnedValue);
        case '+':
            return Number(innerReturnedValue);
        case '~':
            return ~Number(innerReturnedValue);
        case '!':
            return !Boolean(innerReturnedValue);
        case 'typeof':
            return typeof innerReturnedValue;
        default:
            return undefined;
    }
}
/**
 * Returns true if the node is a direct branch body of a conditional or loop statement —
 * i.e., the consequent/alternate of an IfStatement or the body of a loop.
 * Used to push and pop branch frames on the stack when entering and exiting branches.
 */
function isBranchBody(node) {
    const { parent } = node;
    if (!parent) {
        return false;
    }
    if (parent.type === 'IfStatement') {
        return node === parent.consequent || node === parent.alternate;
    }
    if (parent.type === 'WhileStatement' ||
        parent.type === 'DoWhileStatement' ||
        parent.type === 'ForStatement' ||
        parent.type === 'ForInStatement' ||
        parent.type === 'ForOfStatement') {
        return node === parent.body;
    }
    return false;
}
