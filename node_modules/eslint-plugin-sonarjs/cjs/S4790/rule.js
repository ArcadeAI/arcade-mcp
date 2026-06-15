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
// https://sonarsource.github.io/rspec/#/rspec/S4790/javascript
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
const message = 'Make sure this weak hash algorithm is not used in a sensitive context here.';
const CRYPTO_UNSECURE_HASH_ALGORITHMS = new Set([
    'md2',
    'md4',
    'md5',
    'md6',
    'haval128',
    'hmacmd5',
    'dsa',
    'ripemd',
    'ripemd128',
    'ripemd160',
    'hmacripemd160',
    'sha1',
]);
const SUBTLE_UNSECURE_HASH_ALGORITHMS = new Set(['sha-1']);
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta),
    create(context) {
        function checkNodejsCrypto(fqn, node) {
            // crypto#createHash
            const { callee, arguments: args } = node;
            if (fqn === 'crypto.createHash') {
                checkUnsecureAlgorithm(callee, args[0], CRYPTO_UNSECURE_HASH_ALGORITHMS);
            }
        }
        function checkSubtleCrypto(fqn, node) {
            // crypto.subtle#digest
            const { callee, arguments: args } = node;
            if (fqn === 'crypto.subtle.digest') {
                checkUnsecureAlgorithm(callee, args[0], SUBTLE_UNSECURE_HASH_ALGORITHMS);
            }
        }
        function checkUnsecureAlgorithm(method, hash, unsecureAlgorithms) {
            const hashAlgorithm = (0, ast_js_1.getUniqueWriteUsageOrNode)(context, hash);
            if ((0, ast_js_1.isStringLiteral)(hashAlgorithm) &&
                unsecureAlgorithms.has(hashAlgorithm.value.toLocaleLowerCase())) {
                context.report({
                    message,
                    node: method,
                });
            }
        }
        return {
            'CallExpression[arguments.length > 0]': (node) => {
                const callExpr = node;
                const fqn = (0, module_js_1.getFullyQualifiedName)(context, callExpr);
                checkNodejsCrypto(fqn, callExpr);
                checkSubtleCrypto(fqn, callExpr);
            },
        };
    },
};
