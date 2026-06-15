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
// https://sonarsource.github.io/rspec/#/rspec/S5876/javascript
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
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const module_js_1 = require("../helpers/module.js");
const ast_js_1 = require("../helpers/ast.js");
const collection_js_1 = require("../helpers/collection.js");
const meta = __importStar(require("./generated-meta.js"));
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            createSession: 'Create a new session during user authentication to prevent session fixation attacks.',
        },
    }),
    create(context) {
        let sessionRegenerate = false;
        function visitCallback(node) {
            if (sessionRegenerate) {
                // terminate recursion once call is detected
                return;
            }
            if (isSessionRegenerate(node)) {
                sessionRegenerate = true;
                return;
            }
            for (const childNode of (0, ancestor_js_1.childrenOf)(node, context.sourceCode.visitorKeys)) {
                visitCallback(childNode);
            }
        }
        function hasSessionFalseOption(callExpression) {
            const opt = callExpression.arguments[1];
            if (opt?.type === 'ObjectExpression') {
                const sessionProp = (0, ast_js_1.getPropertyWithValue)(context, opt, 'session', false);
                return !!sessionProp;
            }
            return false;
        }
        return {
            CallExpression: (node) => {
                const callExpression = node;
                if ((0, module_js_1.getFullyQualifiedName)(context, callExpression) === 'passport.authenticate') {
                    if (hasSessionFalseOption(callExpression)) {
                        return;
                    }
                    const parent = (0, collection_js_1.last)(context.sourceCode.getAncestors(node));
                    if (parent.type === 'CallExpression') {
                        const callback = (0, ast_js_1.getValueOfExpression)(context, parent.arguments[2], 'FunctionExpression');
                        if (callback?.type === 'FunctionExpression') {
                            sessionRegenerate = false;
                            visitCallback(callback);
                            if (!sessionRegenerate) {
                                context.report({ node: callback, messageId: 'createSession' });
                            }
                        }
                    }
                }
            },
        };
    },
};
function isSessionRegenerate(node) {
    return (node.type === 'CallExpression' &&
        node.callee.type === 'MemberExpression' &&
        (0, ast_js_1.isIdentifier)(node.callee.property, 'regenerate'));
}
