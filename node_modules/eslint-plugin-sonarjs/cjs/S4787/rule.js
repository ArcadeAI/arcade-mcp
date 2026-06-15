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
// https://sonarsource.github.io/rspec/#/rspec/S4787/javascript
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
const getEncryptionRuleModule = (clientSideMethods, serverSideMethods) => ({
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            safeEncryption: 'Make sure that encrypting data is safe here.',
        },
    }),
    create(context) {
        // for client side
        let usingCryptoInFile = false;
        return {
            Program() {
                // init flag for each file
                usingCryptoInFile = false;
            },
            MemberExpression(node) {
                // detect 'SubtleCrypto' object
                // which can be retrieved by 'crypto.subtle' or 'window.crypto.subtle'
                const { object, property } = node;
                if ((0, ast_js_1.isIdentifier)(property, 'subtle') &&
                    ((0, ast_js_1.isIdentifier)(object, 'crypto') || (0, ast_js_1.isMemberWithProperty)(object, 'crypto'))) {
                    usingCryptoInFile = true;
                }
            },
            'CallExpression:exit'(node) {
                const { callee } = node;
                if (usingCryptoInFile) {
                    // e.g.: crypto.subtle.encrypt()
                    checkForClientSide(callee, context, clientSideMethods);
                }
                // e.g.
                // const crypto = require("crypto");
                // const cipher = crypto.createCipher(alg, key);
                checkForServerSide(callee, context, serverSideMethods);
            },
        };
    },
});
function checkForServerSide(callee, context, serverSideMethods) {
    const fqn = (0, module_js_1.getFullyQualifiedName)(context, callee);
    if (serverSideMethods.some(method => fqn === `crypto.${method}`)) {
        context.report({
            messageId: 'safeEncryption',
            node: callee,
        });
    }
}
function checkForClientSide(callee, context, clientSideMethods) {
    if ((0, ast_js_1.isIdentifier)(callee, ...clientSideMethods) ||
        (0, ast_js_1.isMemberWithProperty)(callee, ...clientSideMethods)) {
        context.report({
            messageId: 'safeEncryption',
            node: callee,
        });
    }
}
const clientSideEncryptMethods = ['encrypt', 'decrypt'];
const serverSideEncryptMethods = [
    'createCipher',
    'createCipheriv',
    'createDecipher',
    'createDecipheriv',
    'publicEncrypt',
    'publicDecrypt',
    'privateEncrypt',
    'privateDecrypt',
];
exports.rule = getEncryptionRuleModule(clientSideEncryptMethods, serverSideEncryptMethods);
