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
// https://sonarsource.github.io/rspec/#/rspec/S5667/javascript
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
const ancestor_js_1 = require("../helpers/ancestor.js");
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const module_js_1 = require("../helpers/module.js");
const ast_js_1 = require("../helpers/ast.js");
const meta = __importStar(require("./generated-meta.js"));
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta),
    create(context) {
        const MESSAGE = 'Enable server hostname verification on this SSL/TLS connection.';
        const SECONDARY_MESSAGE = 'Set "rejectUnauthorized" to "true".';
        function checkSensitiveArgument(callExpression, sensitiveArgumentIndex) {
            if (callExpression.arguments.length < sensitiveArgumentIndex + 1) {
                return;
            }
            const sensitiveArgument = callExpression.arguments[sensitiveArgumentIndex];
            const secondaryLocations = [];
            let shouldReport = false;
            const argumentValue = (0, ast_js_1.getValueOfExpression)(context, sensitiveArgument, 'ObjectExpression');
            if (!argumentValue) {
                return;
            }
            if (sensitiveArgument !== argumentValue) {
                secondaryLocations.push((0, location_js_1.toSecondaryLocation)(argumentValue));
            }
            const unsafeRejectUnauthorizedConfiguration = (0, ast_js_1.getPropertyWithValue)(context, argumentValue, 'rejectUnauthorized', false);
            if (unsafeRejectUnauthorizedConfiguration) {
                secondaryLocations.push((0, location_js_1.toSecondaryLocation)(unsafeRejectUnauthorizedConfiguration, SECONDARY_MESSAGE));
                shouldReport = true;
            }
            const checkServerIdentityProperty = (0, ast_js_1.getProperty)(argumentValue, 'checkServerIdentity', context);
            if (checkServerIdentityProperty &&
                shouldReportOnCheckServerIdentityCallBack(checkServerIdentityProperty)) {
                secondaryLocations.push((0, location_js_1.toSecondaryLocation)(checkServerIdentityProperty));
                shouldReport = true;
            }
            if (shouldReport) {
                (0, location_js_1.report)(context, {
                    node: callExpression.callee,
                    message: MESSAGE,
                }, secondaryLocations);
            }
        }
        function shouldReportOnCheckServerIdentityCallBack(checkServerIdentityProperty) {
            let baseFunction;
            baseFunction = (0, ast_js_1.getValueOfExpression)(context, checkServerIdentityProperty.value, 'FunctionExpression');
            baseFunction ??= (0, ast_js_1.getValueOfExpression)(context, checkServerIdentityProperty.value, 'ArrowFunctionExpression');
            if (baseFunction?.body.type === 'BlockStatement') {
                const returnStatements = ReturnStatementsVisitor.getReturnStatements(baseFunction.body, context);
                if (returnStatements.every(r => {
                    return (!r.argument || (0, ast_js_1.getValueOfExpression)(context, r.argument, 'Literal')?.value === true);
                })) {
                    return true;
                }
            }
            return false;
        }
        return {
            CallExpression: (node) => {
                const callExpression = node;
                const fqn = (0, module_js_1.getFullyQualifiedName)(context, callExpression);
                if (fqn === 'https.request') {
                    checkSensitiveArgument(callExpression, 0);
                }
                if (fqn === 'request.get') {
                    checkSensitiveArgument(callExpression, 0);
                }
                if (fqn === 'tls.connect') {
                    checkSensitiveArgument(callExpression, 2);
                }
            },
        };
    },
};
class ReturnStatementsVisitor {
    constructor() {
        this.returnStatements = [];
    }
    static getReturnStatements(node, context) {
        const visitor = new ReturnStatementsVisitor();
        visitor.visit(node, context);
        return visitor.returnStatements;
    }
    visit(root, context) {
        const visitNode = (node) => {
            switch (node.type) {
                case 'ReturnStatement':
                    this.returnStatements.push(node);
                    break;
                case 'FunctionDeclaration':
                case 'FunctionExpression':
                case 'ArrowFunctionExpression':
                    return;
            }
            for (const childNode of (0, ancestor_js_1.childrenOf)(node, context.sourceCode.visitorKeys)) {
                visitNode(childNode);
            }
        };
        visitNode(root);
    }
}
