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
// https://sonarsource.github.io/rspec/#/rspec/S6486/javascript
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
        messages: {
            noGeneratedKeys: 'Do not use generated values for keys of React list components.',
        },
    }),
    create(context) {
        return {
            "JSXAttribute[name.name='key']": (pNode) => {
                // hack: it's not possible to type the argument node from TSESTree
                const node = pNode;
                const value = node.value;
                if (value?.type !== 'JSXExpressionContainer') {
                    // key='foo' or just simply 'key'
                    return;
                }
                checkPropValue(context, value.expression);
            },
        };
    },
};
function checkPropValue(context, node) {
    if (isGeneratedExpression(node)) {
        // key={bar}
        context.report({
            messageId: 'noGeneratedKeys',
            node: node,
        });
        return;
    }
    if (node.type === 'TemplateLiteral') {
        // key={`foo-${bar}`}
        if (node.expressions.some(isGeneratedExpression)) {
            context.report({
                messageId: 'noGeneratedKeys',
                node: node,
            });
        }
        return;
    }
    if (node.type === 'BinaryExpression') {
        // key={'foo' + bar}
        const callExpressions = getCallExpressionsFromBinaryExpression(node);
        if (callExpressions.some(isGeneratedExpression)) {
            context.report({
                messageId: 'noGeneratedKeys',
                node: node,
            });
        }
        return;
    }
    if (node.type === 'CallExpression' &&
        node.callee?.type === 'MemberExpression' &&
        node.callee.object &&
        isGeneratedExpression(node.callee.object) &&
        node.callee.property?.type === 'Identifier' &&
        node.callee.property.name === 'toString') {
        // key={bar.toString()}
        context.report({
            messageId: 'noGeneratedKeys',
            node: node,
        });
        return;
    }
    if (node.type === 'CallExpression' &&
        node.callee?.type === 'Identifier' &&
        node.callee.name === 'String' &&
        Array.isArray(node.arguments) &&
        node.arguments.length > 0 &&
        isGeneratedExpression(node.arguments[0])) {
        // key={String(bar)}
        context.report({
            messageId: 'noGeneratedKeys',
            node: node.arguments[0],
        });
    }
}
function isGeneratedExpression(node) {
    return isMathRandom(node) || isDateNow(node);
    function isMathRandom(node) {
        return (node.type === 'CallExpression' &&
            (0, ast_js_1.isMemberExpression)(node.callee, 'Math', 'random'));
    }
    function isDateNow(node) {
        return (node.type === 'CallExpression' &&
            (0, ast_js_1.isMemberExpression)(node.callee, 'Date', 'now'));
    }
}
function getCallExpressionsFromBinaryExpression(side) {
    if (side.type === 'CallExpression') {
        return side;
    }
    if (side.type === 'BinaryExpression') {
        // recurse
        const left = getCallExpressionsFromBinaryExpression(side.left);
        const right = getCallExpressionsFromBinaryExpression(side.right);
        return [].concat(left, right).filter(Boolean);
    }
    return null;
}
