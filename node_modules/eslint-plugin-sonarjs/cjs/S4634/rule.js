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
// https://sonarsource.github.io/rspec/#/rspec/S4634/javascript
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
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        hasSuggestions: true,
        messages: {
            promiseAction: 'Replace this trivial promise with "Promise.{{action}}".',
            suggestPromiseAction: 'Replace with "Promise.{{action}}"',
        },
    }),
    create(context) {
        return {
            NewExpression: (node) => {
                const newExpr = node;
                const executor = getPromiseExecutor(newExpr, context);
                if (executor) {
                    checkExecutor(newExpr, executor, context);
                }
            },
        };
    },
};
function getPromiseExecutor(node, context) {
    if (node.callee.type === 'Identifier' &&
        context.sourceCode.getText(node.callee) === 'Promise' &&
        node.arguments.length === 1) {
        return node.arguments[0];
    }
    return undefined;
}
function checkExecutor(newExpr, executor, context) {
    if (!(0, ast_js_1.isFunctionNode)(executor)) {
        return;
    }
    const { params, body } = executor;
    const [resolveParameterDeclaration, rejectParameterDeclaration] = params;
    const resolveParameterName = getParameterName(resolveParameterDeclaration);
    const rejectParameterName = getParameterName(rejectParameterDeclaration);
    const bodyExpression = getOnlyBodyExpression(body);
    if (bodyExpression?.type === 'CallExpression') {
        const { callee, arguments: args } = bodyExpression;
        if (callee.type === 'Identifier') {
            const action = getPromiseAction(callee.name, resolveParameterName, rejectParameterName);
            if (action && args.length === 1) {
                context.report({
                    messageId: 'promiseAction',
                    data: {
                        action,
                    },
                    node: newExpr.callee,
                    suggest: [
                        {
                            messageId: 'suggestPromiseAction',
                            data: {
                                action,
                            },
                            fix: fixer => {
                                const argText = context.sourceCode.getText(args[0]);
                                return fixer.replaceText(newExpr, `Promise.${action}(${argText})`);
                            },
                        },
                    ],
                });
            }
        }
    }
}
function getOnlyBodyExpression(node) {
    let bodyExpression;
    if (node.type === 'BlockStatement') {
        if (node.body.length === 1) {
            const statement = node.body[0];
            if (statement.type === 'ExpressionStatement') {
                bodyExpression = statement.expression;
            }
        }
    }
    else {
        bodyExpression = node;
    }
    return bodyExpression;
}
function getPromiseAction(callee, resolveParameterName, rejectParameterName) {
    switch (callee) {
        case resolveParameterName:
            return 'resolve';
        case rejectParameterName:
            return 'reject';
        default:
            return undefined;
    }
}
function getParameterName(node) {
    return node?.type === 'Identifier' ? node.name : undefined;
}
