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
// https://sonarsource.github.io/rspec/#/rspec/S5659/javascript
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
const location_js_1 = require("../helpers/location.js");
const meta = __importStar(require("./generated-meta.js"));
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta),
    create(context) {
        const SIGN_MESSAGE = 'Use only strong cipher algorithms when signing this JWT.';
        const VERIFY_MESSAGE = 'Use only strong cipher algorithms when verifying the signature of this JWT.';
        const SECONDARY_MESSAGE = `The "algorithms" option should be defined and should not contain 'none'.`;
        function checkCallToSign(callExpression, thirdArgumentValue, secondaryLocations) {
            const unsafeAlgorithmProperty = (0, ast_js_1.getPropertyWithValue)(context, thirdArgumentValue, 'algorithm', 'none');
            if (unsafeAlgorithmProperty) {
                const unsafeAlgorithmValue = (0, ast_js_1.getValueOfExpression)(context, unsafeAlgorithmProperty.value, 'Literal');
                if (unsafeAlgorithmValue && unsafeAlgorithmValue !== unsafeAlgorithmProperty.value) {
                    secondaryLocations.push(unsafeAlgorithmValue);
                }
                raiseIssueOn(callExpression.callee, SIGN_MESSAGE, secondaryLocations);
            }
        }
        function checkCallToVerify(callExpression, publicKey, thirdArgumentValue, secondaryLocations) {
            const algorithmsProperty = (0, ast_js_1.getProperty)(thirdArgumentValue, 'algorithms', context);
            if (!algorithmsProperty) {
                if ((0, ast_js_1.isNullLiteral)(publicKey)) {
                    raiseIssueOn(callExpression.callee, VERIFY_MESSAGE, secondaryLocations);
                }
                return;
            }
            const algorithmsValue = (0, ast_js_1.getValueOfExpression)(context, algorithmsProperty.value, 'ArrayExpression');
            if (!algorithmsValue) {
                return;
            }
            const algorithmsContainNone = algorithmsValue.elements.some(e => {
                const value = (0, ast_js_1.getValueOfExpression)(context, e, 'Literal');
                return value?.value === 'none';
            });
            if (algorithmsContainNone) {
                if (algorithmsProperty.value !== algorithmsValue) {
                    secondaryLocations.push(algorithmsValue);
                }
                raiseIssueOn(callExpression.callee, VERIFY_MESSAGE, secondaryLocations);
            }
        }
        function raiseIssueOn(node, message, secondaryLocations) {
            (0, location_js_1.report)(context, {
                node,
                message,
            }, secondaryLocations.map(node => (0, location_js_1.toSecondaryLocation)(node, SECONDARY_MESSAGE)));
        }
        return {
            CallExpression: (node) => {
                const callExpression = node;
                const fqn = (0, module_js_1.getFullyQualifiedName)(context, callExpression);
                const isCallToSign = fqn === 'jsonwebtoken.sign';
                const isCallToVerify = fqn === 'jsonwebtoken.verify';
                if (!isCallToSign && !isCallToVerify) {
                    return;
                }
                if (callExpression.arguments.length < 3) {
                    // algorithm(s) property is contained in third argument of "sign" and "verify" calls
                    return;
                }
                const thirdArgument = callExpression.arguments[2];
                const thirdArgumentValue = (0, ast_js_1.getValueOfExpression)(context, thirdArgument, 'ObjectExpression');
                if (!thirdArgumentValue) {
                    return;
                }
                const secondaryLocations = [thirdArgumentValue];
                if (thirdArgumentValue !== thirdArgument) {
                    secondaryLocations.push(thirdArgument);
                }
                if (isCallToSign) {
                    checkCallToSign(callExpression, thirdArgumentValue, secondaryLocations);
                }
                const secondArgument = callExpression.arguments[1];
                if (isCallToVerify) {
                    checkCallToVerify(callExpression, secondArgument, thirdArgumentValue, secondaryLocations);
                }
            },
        };
    },
};
