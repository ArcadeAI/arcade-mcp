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
// https://sonarsource.github.io/rspec/#/rspec/S2077/javascript
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
const module_js_1 = require("../helpers/module.js");
const ast_js_1 = require("../helpers/ast.js");
const meta = __importStar(require("./generated-meta.js"));
// Dictionary with fully qualified names of functions and indices of their
// parameters to analyze for hardcoded credentials.
const secretSignatures = {
    'cookie-parser': [0],
    'cookie-parser.JSONCookie': [1],
    'cookie-parser.signedCookies': [1],
    'cookie-parser.signedCookie': [1],
    'crypto.X509Certificate.checkPrivateKey': [0],
    'crypto.createDiffieHellman.setPrivateKey': [0],
    'crypto.createECDH.setPrivateKey': [0],
    'crypto.createHmac': [1],
    'crypto.createSecretKey': [0],
    'crypto.createSign.sign': [0],
    'crypto.createVerify.verify': [0],
    'crypto.privateDecrypt': [0],
    'crypto.privateEncrypt': [0],
    'crypto.sign': [2],
    'crypto.verify': [2],
    'jose.SignJWT': [0],
    'jose.jwtVerify': [1],
    'jsonwebtoken.sign': [1],
    'jsonwebtoken.verify': [1],
    'ldapjs.createClient.bind': [1],
    'node-jose.JWK.asKey': [0],
    'superagent.auth': [0],
};
// Dictionary with fully qualified names of functions, argument index containing
// the options object, and property name(s) that hold the secret.
const secretObjectSignatures = {
    'cookie-session': { argIndex: 0, propertyName: 'keys' },
    'express-session': { argIndex: 0, propertyName: 'secret' },
    'typeorm.createConnection': { argIndex: 0, propertyName: 'password' },
    'mysql.createConnection': { argIndex: 0, propertyName: 'password' },
    'mysql.createPool': { argIndex: 0, propertyName: 'password' },
    'mysql2.createConnection': { argIndex: 0, propertyName: 'password' },
    'mysql2.createPool': { argIndex: 0, propertyName: 'password' },
};
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {},
    }),
    create(context) {
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
        function getSecondaryLocations(expr) {
            if (expr.type === 'Identifier' && hardcodedVariables.has(expr.name)) {
                const nodeName = hardcodedVariables.get(expr.name);
                if (nodeName) {
                    return [(0, location_js_1.toSecondaryLocation)(nodeName, 'Hardcoded value assigned here')];
                }
            }
            return [];
        }
        function reportIssue(callExpression, secretExpr) {
            (0, location_js_1.report)(context, {
                message: 'Revoke and change this password, as it is compromised.',
                loc: callExpression.callee.loc,
            }, getSecondaryLocations(secretExpr));
        }
        function checkSecretArgument(callExpression, fqn) {
            secretSignatures[fqn].forEach(index => {
                const arg = callExpression.arguments[index];
                if (arg && arg.type !== 'SpreadElement' && isHardcodedString(arg)) {
                    reportIssue(callExpression, arg);
                }
            });
        }
        function checkSecretProperty(callExpression, fqn) {
            const { argIndex, propertyName } = secretObjectSignatures[fqn];
            const arg = callExpression.arguments[argIndex];
            if (!arg) {
                return;
            }
            const objectExpr = (0, ast_js_1.getValueOfExpression)(context, arg, 'ObjectExpression');
            if (!objectExpr) {
                return;
            }
            const secretProperty = (0, ast_js_1.getProperty)(objectExpr, propertyName, context);
            if (!secretProperty) {
                return;
            }
            const secretValue = secretProperty.value;
            if (isHardcodedString(secretValue)) {
                reportIssue(callExpression, secretValue);
            }
            else if (secretValue.type === 'ArrayExpression') {
                for (const element of secretValue.elements) {
                    if (element && element.type !== 'SpreadElement' && isHardcodedString(element)) {
                        reportIssue(callExpression, element);
                    }
                }
            }
        }
        return {
            Program() {
                hardcodedVariables.clear();
            },
            VariableDeclarator(node) {
                if (node.id.type === 'Identifier' && node.init && isHardcodedString(node.init)) {
                    hardcodedVariables.set(node.id.name, node.init);
                }
            },
            CallExpression(node) {
                const fqn = (0, module_js_1.getFullyQualifiedName)(context, node);
                if (!fqn) {
                    return;
                }
                if (node.arguments.length > 0 && fqn in secretSignatures) {
                    checkSecretArgument(node, fqn);
                }
                if (fqn in secretObjectSignatures) {
                    checkSecretProperty(node, fqn);
                }
            },
        };
    },
};
