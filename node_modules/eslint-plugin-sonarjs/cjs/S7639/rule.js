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
// https://sonarsource.github.io/rspec/#/rspec/S7639/javascript
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
const BLOCKCHAIN_MODULES = ['ethers', 'viem/accounts', 'tronweb'];
const MNEMONIC_FUNCTIONS = ['fromPhrase', 'mnemonicToAccount', 'fromMnemonic'];
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            reviewBlockchainSeedPhrase: `Revoke and change this seed phrase, as it is compromised.`,
        },
    }),
    create(context) {
        let isBlockchainModuleImported = false;
        const hardcodedVariables = new Map();
        function isHardcodedString(expr) {
            switch (expr.type) {
                case 'Literal':
                    return typeof expr.value === 'string';
                case 'TemplateLiteral':
                    return expr.expressions.length === 0;
                case 'Identifier':
                    return hardcodedVariables.has(expr.name);
                default:
                    return false;
            }
        }
        function getReportNode(expr) {
            // If it's an identifier that references a hardcoded string, report the original declaration
            if (expr.type === 'Identifier' && hardcodedVariables.has(expr.name)) {
                const nodeName = hardcodedVariables.get(expr.name);
                if (nodeName) {
                    return nodeName;
                }
            }
            return expr;
        }
        function isMnemonicFunction(callee) {
            return MNEMONIC_FUNCTIONS.some(func => (0, ast_js_1.isMemberWithProperty)(callee, func) || (0, ast_js_1.isIdentifier)(callee, func));
        }
        return {
            Program() {
                isBlockchainModuleImported = false;
                hardcodedVariables.clear();
            },
            ImportDeclaration(node) {
                if (BLOCKCHAIN_MODULES.includes(node.source.value)) {
                    isBlockchainModuleImported = true;
                }
            },
            VariableDeclarator(node) {
                if (isBlockchainModuleImported &&
                    node.id.type === 'Identifier' &&
                    node.init &&
                    ((node.init.type === 'Literal' && typeof node.init.value === 'string') ||
                        (node.init.type === 'TemplateLiteral' && node.init.expressions.length === 0))) {
                    hardcodedVariables.set(node.id.name, node.init);
                }
            },
            CallExpression(node) {
                if ((0, ast_js_1.isRequireModule)(node, ...BLOCKCHAIN_MODULES)) {
                    isBlockchainModuleImported = true;
                    return;
                }
                if (isBlockchainModuleImported &&
                    isMnemonicFunction(node.callee) &&
                    node.arguments.length > 0 &&
                    node.arguments[0].type !== 'SpreadElement' &&
                    isHardcodedString(node.arguments[0])) {
                    context.report({
                        messageId: 'reviewBlockchainSeedPhrase',
                        node: getReportNode(node.arguments[0]),
                    });
                }
            },
        };
    },
};
