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
// https://sonarsource.github.io/rspec/#/rspec/S3699
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
const EMPTY_RETURN_VALUE_KEYWORDS = new Set([
    'TSVoidKeyword',
    'TSNeverKeyword',
    'TSUndefinedKeyword',
]);
function isReturnValueUsed(callExpr) {
    const { parent } = callExpr;
    if (!parent) {
        return false;
    }
    if (parent.type === 'LogicalExpression') {
        return parent.left === callExpr;
    }
    if (parent.type === 'SequenceExpression') {
        return parent.expressions.at(-1) === callExpr && isReturnValueUsed(parent);
    }
    if (parent.type === 'ConditionalExpression') {
        return parent.test === callExpr;
    }
    return (parent.type !== 'ExpressionStatement' &&
        parent.type !== 'ArrowFunctionExpression' &&
        parent.type !== 'UnaryExpression' &&
        parent.type !== 'AwaitExpression' &&
        parent.type !== 'ReturnStatement' &&
        parent.type !== 'ThrowStatement');
}
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            removeUseOfOutput: 'Remove this use of the output from "{{name}}"; "{{name}}" doesn\'t return anything.',
        },
    }),
    create(context) {
        const callExpressionsToCheck = new Map();
        const functionsWithReturnValue = new Set();
        return {
            CallExpression(node) {
                const callExpr = node;
                if (!isReturnValueUsed(callExpr)) {
                    return;
                }
                const scope = context.sourceCode.getScope(callExpr);
                const reference = scope.references.find(ref => ref.identifier === callExpr.callee);
                if (reference?.resolved) {
                    const variable = reference.resolved;
                    if (variable.defs.length === 1) {
                        const definition = variable.defs[0];
                        if (definition.type === 'FunctionName') {
                            callExpressionsToCheck.set(reference.identifier, definition.node);
                        }
                        else if (definition.type === 'Variable') {
                            const { init } = definition.node;
                            if (init && ((0, ast_js_1.isFunctionExpression)(init) || (0, ast_js_1.isArrowFunctionExpression)(init))) {
                                callExpressionsToCheck.set(reference.identifier, init);
                            }
                        }
                    }
                }
            },
            ReturnStatement(node) {
                const returnStmt = node;
                if (returnStmt.argument) {
                    const ancestors = [...context.sourceCode.getAncestors(node)].reverse();
                    const functionNode = ancestors.find(node => node.type === 'FunctionExpression' ||
                        node.type === 'FunctionDeclaration' ||
                        node.type === 'ArrowFunctionExpression');
                    functionsWithReturnValue.add(functionNode);
                }
            },
            ArrowFunctionExpression(node) {
                const arrowFunc = node;
                if (arrowFunc.expression) {
                    functionsWithReturnValue.add(arrowFunc);
                }
            },
            ':function'(node) {
                const func = node;
                if (func.async ||
                    func.generator ||
                    (func.body.type === 'BlockStatement' && func.body.body.length === 0)) {
                    functionsWithReturnValue.add(func);
                }
            },
            TSDeclareFunction(node) {
                const declareFunction = node;
                if (declareFunction.returnType?.typeAnnotation.type &&
                    !EMPTY_RETURN_VALUE_KEYWORDS.has(declareFunction.returnType?.typeAnnotation.type)) {
                    functionsWithReturnValue.add(declareFunction);
                }
            },
            'Program:exit'() {
                for (const [callee, functionDeclaration] of callExpressionsToCheck.entries()) {
                    if (!functionsWithReturnValue.has(functionDeclaration)) {
                        context.report({
                            messageId: 'removeUseOfOutput',
                            node: callee,
                            data: { name: callee.name },
                        });
                    }
                }
            },
        };
    },
};
