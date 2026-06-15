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
// https://sonarsource.github.io/rspec/#/rspec/S4426/javascript
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
const MINIMAL_MODULUS_LENGTH = 2048;
const MINIMAL_DIVISOR_LENGTH = 224;
const WEAK_CURVES = new Set([
    'secp112r1',
    'secp112r2',
    'secp128r1',
    'secp128r2',
    'secp160k1',
    'secp160r1',
    'secp160r2',
    'secp160r2',
    'secp192k1',
    'secp192r1',
    'prime192v2',
    'prime192v3',
    'sect113r1',
    'sect113r2',
    'sect131r1',
    'sect131r2',
    'sect163k1',
    'sect163r1',
    'sect163r2',
    'sect193r1',
    'sect193r2',
    'c2tnb191v1',
    'c2tnb191v2',
    'c2tnb191v3',
]);
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            modulusLength: 'Use a modulus length of at least {{minimalLength}} bits for {{algorithm}} cipher algorithm.',
            divisorLength: 'Use a divisor length of at least {{minimalLength}} bits for {{algorithm}} cipher algorithm.',
            strongerCurve: `{{curve}} doesn't provide enough security. Use a stronger curve.`,
        },
    }),
    create(context) {
        function getNumericValue(node) {
            const literal = (0, ast_js_1.getValueOfExpression)(context, node, 'Literal');
            if (literal && typeof literal.value === 'number') {
                return literal.value;
            }
            return undefined;
        }
        function checkRsaAndDsaOptions(algorithm, options) {
            const modulusProperty = (0, ast_js_1.getProperty)(options, 'modulusLength', context);
            const modulusLength = getNumericValue(modulusProperty?.value);
            if (modulusProperty && modulusLength && modulusLength < MINIMAL_MODULUS_LENGTH) {
                context.report({
                    node: modulusProperty,
                    messageId: 'modulusLength',
                    data: {
                        minimalLength: MINIMAL_MODULUS_LENGTH.toString(),
                        algorithm,
                    },
                });
            }
            const divisorProperty = (0, ast_js_1.getProperty)(options, 'divisorLength', context);
            const divisorLength = getNumericValue(divisorProperty?.value);
            if (divisorProperty && divisorLength && divisorLength < MINIMAL_DIVISOR_LENGTH) {
                context.report({
                    node: divisorProperty,
                    messageId: 'divisorLength',
                    data: {
                        minimalLength: MINIMAL_DIVISOR_LENGTH.toString(),
                        algorithm,
                    },
                });
            }
        }
        function checkEcCurve(options) {
            const namedCurveProperty = (0, ast_js_1.getProperty)(options, 'namedCurve', context);
            const namedCurve = (0, ast_js_1.getValueOfExpression)(context, namedCurveProperty?.value, 'Literal')?.value?.toString();
            if (namedCurveProperty && namedCurve && WEAK_CURVES.has(namedCurve)) {
                context.report({
                    node: namedCurveProperty,
                    messageId: 'strongerCurve',
                    data: {
                        curve: namedCurve,
                    },
                });
            }
        }
        return {
            CallExpression: (node) => {
                const callExpression = node;
                const { callee } = callExpression;
                if (callee.type === 'MemberExpression' &&
                    (0, ast_js_1.isIdentifier)(callee.property, 'generateKeyPair', 'generateKeyPairSync')) {
                    if (callExpression.arguments.length < 2) {
                        return;
                    }
                    const [algorithmArg, options] = callExpression.arguments;
                    const optionsArg = (0, ast_js_1.getValueOfExpression)(context, options, 'ObjectExpression');
                    if (!optionsArg) {
                        return;
                    }
                    const algorithm = (0, ast_js_1.getValueOfExpression)(context, algorithmArg, 'Literal')?.value;
                    if (algorithm === 'rsa' || algorithm === 'dsa') {
                        checkRsaAndDsaOptions(algorithm, optionsArg);
                    }
                    else if (algorithm === 'ec') {
                        checkEcCurve(optionsArg);
                    }
                }
            },
        };
    },
};
