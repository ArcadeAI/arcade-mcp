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
// https://sonarsource.github.io/rspec/#/rspec/S930
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
const location_js_1 = require("../helpers/location.js");
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const ast_js_1 = require("../helpers/ast.js");
const meta = __importStar(require("./generated-meta.js"));
const message = 'This function expects {{expectedArguments}}, but {{providedArguments}} provided.';
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            tooManyArguments: message,
        },
    }),
    create(context) {
        const callExpressionsToCheck = [];
        const usingArguments = new Set();
        const emptyFunctions = new Set();
        return {
            CallExpression(callExpr) {
                if ((0, ast_js_1.isIdentifier)(callExpr.callee)) {
                    const reference = context.sourceCode
                        .getScope(callExpr)
                        .references.find(ref => ref.identifier === callExpr.callee);
                    const definition = reference && getSingleDefinition(reference);
                    if (definition) {
                        if (definition.type === 'FunctionName') {
                            checkFunction(callExpr, definition.node);
                        }
                        else if (definition.type === 'Variable') {
                            const { init } = definition.node;
                            if (init && ((0, ast_js_1.isFunctionExpression)(init) || (0, ast_js_1.isArrowFunctionExpression)(init))) {
                                checkFunction(callExpr, init);
                            }
                        }
                    }
                }
                else if ((0, ast_js_1.isArrowFunctionExpression)(callExpr.callee) ||
                    (0, ast_js_1.isFunctionExpression)(callExpr.callee)) {
                    // IIFE
                    checkFunction(callExpr, callExpr.callee);
                }
            },
            ':function'(node) {
                const fn = node;
                if (fn.body.type === 'BlockStatement' &&
                    fn.body.body.length === 0 &&
                    fn.params.length === 0) {
                    emptyFunctions.add(node);
                }
            },
            'FunctionDeclaration > BlockStatement Identifier'(node) {
                checkArguments(node);
            },
            'FunctionExpression > BlockStatement Identifier'(node) {
                checkArguments(node);
            },
            'Program:exit'() {
                for (const { callExpr, functionNode } of callExpressionsToCheck) {
                    if (!usingArguments.has(functionNode) && !emptyFunctions.has(functionNode)) {
                        reportIssue(callExpr, functionNode);
                    }
                }
            },
        };
        function checkArguments(identifier) {
            if (identifier.name === 'arguments') {
                const reference = context.sourceCode
                    .getScope(identifier)
                    .references.find(ref => ref.identifier === identifier);
                const definition = reference && getSingleDefinition(reference);
                // special `arguments` variable has no definition
                if (!definition) {
                    const ancestors = context.sourceCode.getAncestors(identifier).reverse();
                    const fn = ancestors.find(node => (0, ast_js_1.isFunctionDeclaration)(node) ||
                        (0, ast_js_1.isFunctionExpression)(node));
                    if (fn) {
                        usingArguments.add(fn);
                    }
                }
            }
        }
        function checkFunction(callExpr, functionNode) {
            const hasRest = functionNode.params.some(param => param.type === 'RestElement');
            if (!hasRest && callExpr.arguments.length > functionNode.params.length) {
                callExpressionsToCheck.push({ callExpr, functionNode });
            }
        }
        function reportIssue(callExpr, functionNode) {
            const paramLength = functionNode.params.length;
            const argsLength = callExpr.arguments.length;
            // prettier-ignore
            const expectedArguments = paramLength === 0 ? "no arguments" :
                paramLength === 1 ? "1 argument" :
                    `${paramLength} arguments`;
            // prettier-ignore
            const providedArguments = argsLength === 0 ? "none was" :
                argsLength === 1 ? "1 was" :
                    `${argsLength} were`;
            (0, location_js_1.report)(context, {
                message,
                messageId: 'tooManyArguments',
                data: {
                    expectedArguments,
                    providedArguments,
                },
                node: callExpr.callee,
            }, getSecondaryLocations(callExpr, functionNode));
        }
        function getSecondaryLocations(callExpr, functionNode) {
            const paramLength = functionNode.params.length;
            const secondaryLocations = [];
            if (paramLength > 0) {
                secondaryLocations.push((0, location_js_1.toSecondaryLocation)(functionNode.params[0], functionNode.params[paramLength - 1], 'Formal parameters'));
            }
            else {
                // as we're not providing parent node, `getMainFunctionTokenLocation` may return `undefined`
                const fnToken = (0, location_js_1.getMainFunctionTokenLocation)(functionNode, undefined, context);
                if (fnToken) {
                    secondaryLocations.push((0, location_js_1.toSecondaryLocation)({ loc: fnToken }, 'Formal parameters'));
                }
            }
            // find actual extra arguments to highlight
            for (const [index, argument] of callExpr.arguments.entries()) {
                if (index >= paramLength) {
                    const { loc } = argument;
                    secondaryLocations.push({
                        message: 'Extra argument',
                        column: loc.start.column,
                        line: loc.start.line,
                        endColumn: loc.end.column,
                        endLine: loc.end.line,
                    });
                }
            }
            return secondaryLocations;
        }
    },
};
function getSingleDefinition(reference) {
    if (reference.resolved) {
        const variable = reference.resolved;
        if (variable.defs.length === 1) {
            return variable.defs[0];
        }
    }
    return undefined;
}
