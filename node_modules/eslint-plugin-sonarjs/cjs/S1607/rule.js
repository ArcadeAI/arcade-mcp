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
// https://sonarsource.github.io/rspec/#/rspec/S1607
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
const module_js_1 = require("../helpers/module.js");
const ast_js_1 = require("../helpers/ast.js");
const meta = __importStar(require("./generated-meta.js"));
const dependencies_js_1 = require("../helpers/package-jsons/dependencies.js");
const all_in_parent_dirs_js_1 = require("../helpers/package-jsons/all-in-parent-dirs.js");
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            removeOrExplainTest: 'Remove this unit test or explain why it is ignored.',
        },
    }),
    create(context) {
        const dependencies = (0, dependencies_js_1.getDependenciesSanitizePaths)(context);
        switch (true) {
            case dependencies.has('jasmine'):
                return jasmineListener();
            case dependencies.has('jest'):
                return jestListener();
            case dependencies.has('mocha'):
                return mochaListener();
            case (0, all_in_parent_dirs_js_1.getManifestsSanitizePaths)(context).length > 0:
                return nodejsListener();
            default:
                return {};
        }
        /**
         * Returns a rule listener specific to Jasmine.
         *
         * Ignoring tests with Jasmine is done by using `xit`, `xdescribe`, or `xcontext`.
         */
        function jasmineListener() {
            return {
                CallExpression(node) {
                    if (isJasmineIgnoredTest(node) && !hasExplanationComment(node)) {
                        context.report({
                            node: node.callee,
                            messageId: 'removeOrExplainTest',
                        });
                    }
                },
            };
        }
        /**
         * Returns a rule listener specific to Jest.
         *
         * Ignoring tests with Jest is done by using `test.skip`, `it.skip`, or `describe.skip`.
         */
        function jestListener() {
            return {
                CallExpression(node) {
                    if (isJestIgnoredTest(node) && !hasExplanationComment(node)) {
                        context.report({
                            node: node.callee,
                            messageId: 'removeOrExplainTest',
                        });
                    }
                },
            };
        }
        /**
         * Returns a rule listener specific to Mocha.
         *
         * Ignoring tests with Mocha is done by using `it.skip`, `describe.skip`, or `context.skip`.
         */
        function mochaListener() {
            return {
                CallExpression(node) {
                    if (isMochaIgnoredTest(node) && !hasExplanationComment(node)) {
                        context.report({
                            node: node.callee,
                            messageId: 'removeOrExplainTest',
                        });
                    }
                },
            };
        }
        /**
         * Returns a rule listener specific to Node.js test runner API.
         *
         * Ignoring tests with Node.js test runner API is done by using either:
         *  - by passing the skip option to the test, i.e. `test('name', { skip: true }, () => {})`, or
         *  - by calling the test context's `skip()` method, i.e. `test.skip('name', t => { t.skip(); })`.
         */
        function nodejsListener() {
            return {
                CallExpression: (node) => {
                    const fqn = (0, module_js_1.getFullyQualifiedName)(context, node.callee);
                    if (fqn !== 'test') {
                        return;
                    }
                    switch (node.arguments.length) {
                        case 2:
                            handleSkipMethod(node);
                            break;
                        case 3:
                            handleSkipOption(node);
                            break;
                        default:
                            return;
                    }
                },
            };
        }
        /**
         * Handle the pattern `test('name', t => { t.skip(); })`.
         */
        function handleSkipMethod(node) {
            const fn = (0, ast_js_1.resolveFunction)(context, node.arguments[1]);
            if (!fn) {
                return;
            }
            const testCtxParam = fn.params[0];
            if (!testCtxParam || !(0, ast_js_1.isIdentifier)(testCtxParam)) {
                return;
            }
            const scopeVariables = context.sourceCode.scopeManager.getDeclaredVariables(fn);
            const testCtxVar = scopeVariables.find(v => v.name === testCtxParam.name);
            if (!testCtxVar) {
                return;
            }
            for (const testCtxRef of testCtxVar.references) {
                const testCtxIden = testCtxRef.identifier;
                const maybeSkipCall = testCtxIden?.parent?.parent;
                if (maybeSkipCall?.type !== 'CallExpression') {
                    continue;
                }
                const skipCall = maybeSkipCall;
                if (!(0, ast_js_1.isMethodInvocation)(skipCall, testCtxIden.name, 'skip', 0)) {
                    continue;
                }
                const skipArg = skipCall.arguments[0];
                if (!skipArg || ((0, ast_js_1.isLiteral)(skipArg) && skipArg.value === '')) {
                    context.report({
                        node: skipCall.callee,
                        messageId: 'removeOrExplainTest',
                    });
                    break;
                }
            }
        }
        /**
         * Handle the pattern `test('name', { skip: true }, () => {})`.
         */
        function handleSkipOption(node) {
            const options = (0, ast_js_1.getValueOfExpression)(context, node.arguments[1], 'ObjectExpression');
            if (!options) {
                return;
            }
            const skipProperty = (0, ast_js_1.getProperty)(options, 'skip', context);
            if (!skipProperty) {
                return;
            }
            const skipValue = (0, ast_js_1.getValueOfExpression)(context, skipProperty.value, 'Literal');
            if (!skipValue || (skipValue.value !== true && skipValue.value !== '')) {
                return;
            }
            context.report({
                node: skipProperty,
                messageId: 'removeOrExplainTest',
            });
        }
        /**
         * Checks if the node denoting a test has an adjacent explanation comment.
         */
        function hasExplanationComment(node) {
            function isAdjacent(comment, node) {
                const commentLine = comment.loc.end.line;
                const nodeLine = node.loc.start.line;
                return Math.abs(commentLine - nodeLine) <= 1;
            }
            function hasContent(comment) {
                return /\p{L}/u.test(comment.value.trim());
            }
            const comments = context.sourceCode.getAllComments();
            return comments.some(comment => isAdjacent(comment, node) && hasContent(comment));
        }
    },
};
function isJasmineIgnoredTest(node) {
    return (0, ast_js_1.isIdentifier)(node.callee, 'xit', 'xdescribe', 'xcontext');
}
function isJestIgnoredTest(node) {
    return ((0, ast_js_1.isMethodInvocation)(node, 'test', 'skip', 0) ||
        (0, ast_js_1.isMethodInvocation)(node, 'it', 'skip', 0) ||
        (0, ast_js_1.isMethodInvocation)(node, 'describe', 'skip', 0) ||
        (0, ast_js_1.isFunctionInvocation)(node, 'xtest', 0) ||
        (0, ast_js_1.isFunctionInvocation)(node, 'xit', 0) ||
        (0, ast_js_1.isFunctionInvocation)(node, 'xdescribe', 0));
}
function isMochaIgnoredTest(node) {
    return ((0, ast_js_1.isMethodInvocation)(node, 'it', 'skip', 0) ||
        (0, ast_js_1.isMethodInvocation)(node, 'describe', 'skip', 0) ||
        (0, ast_js_1.isMethodInvocation)(node, 'context', 'skip', 0));
}
