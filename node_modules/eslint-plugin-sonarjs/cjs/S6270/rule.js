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
// https://sonarsource.github.io/rspec/#/rspec/S6270/javascript
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
const module_js_1 = require("../helpers/module.js");
const location_js_1 = require("../helpers/location.js");
const result_js_1 = require("../helpers/result.js");
const iam_js_1 = require("../helpers/aws/iam.js");
const cdk_js_1 = require("../helpers/aws/cdk.js");
const meta = __importStar(require("./generated-meta.js"));
const AWS_PRINCIPAL_PROPERTY = 'AWS';
const ARN_PRINCIPAL = 'aws_cdk_lib.aws_iam.ArnPrincipal';
const MESSAGES = {
    message: 'Make sure granting public access is safe here.',
    secondary: 'Related effect',
};
exports.rule = (0, iam_js_1.AwsIamPolicyTemplate)(publicAccessStatementChecker, (0, generate_meta_js_1.generateMeta)(meta));
function publicAccessStatementChecker(expr, ctx, options) {
    const properties = (0, result_js_1.getResultOfExpression)(ctx, expr);
    const effect = (0, iam_js_1.getSensitiveEffect)(properties, ctx, options);
    const principal = getSensitivePrincipal(properties, ctx, options);
    if (effect.isMissing && principal) {
        (0, location_js_1.report)(ctx, {
            message: MESSAGES.message,
            node: principal,
        });
    }
    else if (effect.isFound && principal) {
        (0, location_js_1.report)(ctx, {
            message: MESSAGES.message,
            node: principal,
        }, [(0, location_js_1.toSecondaryLocation)(effect.node, MESSAGES.secondary)]);
    }
}
function getSensitivePrincipal(properties, ctx, options) {
    const principal = properties.getProperty(options.principals.property);
    if (!principal.isFound) {
        return null;
    }
    else if (options.principals.type === 'FullyQualifiedName') {
        return getSensitivePrincipalFromFullyQualifiedName(ctx, principal.node, options);
    }
    else {
        return getSensitivePrincipalFromJson(ctx, principal.node);
    }
}
function getSensitivePrincipalFromFullyQualifiedName(ctx, node, options) {
    return getPrincipalNewExpressions(node).find(expr => isSensitivePrincipalNewExpression(ctx, expr, options));
}
function getPrincipalNewExpressions(node) {
    const newExpressions = [];
    if ((0, ast_js_1.isArrayExpression)(node)) {
        for (const element of node.elements) {
            if (element?.type === 'NewExpression') {
                newExpressions.push(element);
            }
        }
    }
    return newExpressions;
}
function getSensitivePrincipalFromJson(ctx, node) {
    return getPrincipalLiterals(node, ctx).find(iam_js_1.isAnyLiteral);
}
function isSensitivePrincipalNewExpression(ctx, newExpression, options) {
    return (options.principals.anyValues ?? []).some(anyValue => {
        if (anyValue === ARN_PRINCIPAL) {
            const argument = newExpression.arguments[0];
            return (0, ast_js_1.isStringLiteral)(argument) && (0, iam_js_1.isAnyLiteral)(argument);
        }
        else {
            return anyValue === (0, cdk_js_1.normalizeFQN)((0, module_js_1.getFullyQualifiedName)(ctx, newExpression.callee));
        }
    });
}
function getPrincipalLiterals(node, ctx) {
    const literals = [];
    if ((0, ast_js_1.isStringLiteral)(node)) {
        literals.push(node);
    }
    else {
        const awsLiterals = (0, result_js_1.getResultOfExpression)(ctx, node)
            .getProperty(AWS_PRINCIPAL_PROPERTY)
            .asStringLiterals();
        literals.push(...awsLiterals);
    }
    return literals;
}
