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
// https://sonarsource.github.io/rspec/#/rspec/S100/javascript
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
const ast_js_1 = require("../helpers/ast.js");
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const collection_js_1 = require("../helpers/collection.js");
const meta = __importStar(require("./generated-meta.js"));
const functionExitSelector = [
    ':matches(',
    ['FunctionExpression', 'ArrowFunctionExpression', 'FunctionDeclaration'].join(','),
    ')',
    ':exit',
].join('');
const functionExpressionProperty = [
    'Property',
    '[key.type="Identifier"]',
    ':matches(',
    ['[value.type="FunctionExpression"]', '[value.type="ArrowFunctionExpression"]'].join(','),
    ')',
].join('');
const functionExpressionVariable = [
    'VariableDeclarator',
    '[id.type="Identifier"]',
    ':matches(',
    ['[init.type="FunctionExpression"]', '[init.type="ArrowFunctionExpression"]'].join(','),
    ')',
].join('');
const DEFAULT_FORMAT = '^[_a-z][a-zA-Z0-9]*$';
const messages = {
    renameFunction: "Rename this '{{function}}' function to match the regular expression '{{format}}'.",
};
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, { messages }),
    create(context) {
        const format = context.options[0]?.format ?? DEFAULT_FORMAT;
        const knowledgeStack = [];
        return {
            [functionExpressionProperty]: (node) => {
                knowledgeStack.push({
                    node: node.key,
                    func: node.value,
                    returnsJSX: returnsJSX(node.value),
                });
            },
            [functionExpressionVariable]: (node) => {
                knowledgeStack.push({
                    node: node.id,
                    func: node.init,
                    returnsJSX: returnsJSX(node.init),
                });
            },
            'MethodDefinition[key.type="Identifier"]': (node) => {
                knowledgeStack.push({
                    node: node.key,
                    func: node.value,
                    returnsJSX: false,
                });
            },
            'FunctionDeclaration[id.type="Identifier"]': (node) => {
                knowledgeStack.push({
                    node: node.id,
                    func: node,
                    returnsJSX: false,
                });
            },
            [functionExitSelector]: (func) => {
                if (func === (0, collection_js_1.last)(knowledgeStack)?.func) {
                    const knowledge = knowledgeStack.pop();
                    if (knowledge && !knowledge.returnsJSX) {
                        const { node } = knowledge;
                        if (!node.name.match(format)) {
                            context.report({
                                messageId: 'renameFunction',
                                data: {
                                    function: node.name,
                                    format,
                                },
                                node,
                            });
                        }
                    }
                }
            },
            ReturnStatement: (node) => {
                const knowledge = (0, collection_js_1.last)(knowledgeStack);
                const ancestors = context.sourceCode.getAncestors(node);
                for (let i = ancestors.length - 1; i >= 0; i--) {
                    if (ast_js_1.functionLike.has(ancestors[i].type)) {
                        const enclosingFunction = ancestors[i];
                        if (knowledge?.func === enclosingFunction && node.argument?.type.startsWith('JSX')) {
                            knowledge.returnsJSX = true;
                        }
                        return;
                    }
                }
            },
        };
    },
};
//handling arrow functions without return statement
function returnsJSX(node) {
    return node.body.type.startsWith('JSX');
}
