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
// https://sonarsource.github.io/rspec/#/rspec/S6333/javascript
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
const cdk_js_1 = require("../helpers/aws/cdk.js");
const result_js_1 = require("../helpers/result.js");
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const module_js_1 = require("../helpers/module.js");
const ast_js_1 = require("../helpers/ast.js");
const meta = __importStar(require("./generated-meta.js"));
const REST_API_PROPERTIES_POSITION = 2;
const RESOURCE_ADD_RESOURCE_PROPERTIES_POSITION = 1;
const RESOURCE_ADD_METHOD_POSITION = 2;
const REST_API_ROOT_PROPERTY = 'root';
const DEFAULT_METHOD_OPTIONS = 'defaultMethodOptions';
const AUTHORIZATION_TYPE = 'authorizationType';
const NONE_AUTHORIZATION_TYPE = 'aws_cdk_lib.aws_apigateway.AuthorizationType.NONE';
const ADD_METHOD = 'addMethod';
const ADD_RESOURCE = 'addResource';
const GET_RESOURCE = 'getResource';
const PARENT_RESOURCE = 'parentResource';
const messages = {
    publicApi: 'Make sure that creating public APIs is safe here.',
    omittedAuthorizationType: 'Omitting "authorizationType" disables authentication. Make sure it is safe here.',
};
const apigatewayChecker = (0, cdk_js_1.AwsCdkCheckArguments)(['omittedAuthorizationType', 'publicApi'], true, AUTHORIZATION_TYPE, { primitives: { invalid: ['NONE'] } });
function consumersFactory(ctx) {
    const defaultAuthorizationTypes = new Map();
    const restApiDefaultCollector = defaultsCollector(REST_API_PROPERTIES_POSITION);
    const resourceDefaultCollector = defaultsCollector(RESOURCE_ADD_RESOURCE_PROPERTIES_POSITION);
    return {
        'aws_cdk_lib.aws_apigateway.CfnMethod': apigatewayChecker,
        'aws_cdk_lib.aws_apigatewayv2.CfnRoute': apigatewayChecker,
        'aws_cdk_lib.aws_apigateway.RestApi': restApiDefaultCollector,
        'aws_cdk_lib.aws_apigateway.RestApi.root': {
            methods: [ADD_METHOD, ADD_RESOURCE, GET_RESOURCE, PARENT_RESOURCE],
            callExpression: (expr, _ctx, fqn) => {
                if (fqn.endsWith(ADD_METHOD)) {
                    checkResourceMethod(expr);
                }
                else if (fqn.endsWith(ADD_RESOURCE)) {
                    resourceDefaultCollector(expr);
                }
            },
        },
    };
    function checkResourceMethod(expr) {
        const properties = (0, result_js_1.getResultOfExpression)(ctx, expr).getArgument(RESOURCE_ADD_METHOD_POSITION);
        const authorizationType = properties.getProperty(AUTHORIZATION_TYPE);
        if (authorizationType.isFound && isSensitiveAuthorizationType(authorizationType.node)) {
            ctx.report({
                messageId: 'publicApi',
                node: authorizationType.node,
            });
        }
        else if (authorizationType.isMissing) {
            const defaultAuthorizationType = getDefaultAuthorizationType(expr.callee);
            if (defaultAuthorizationType == null) {
                ctx.report({
                    messageId: 'omittedAuthorizationType',
                    node: authorizationType.node,
                });
            }
            else if (isSensitiveAuthorizationType(defaultAuthorizationType)) {
                ctx.report({
                    messageId: 'publicApi',
                    node: expr,
                });
            }
        }
    }
    function getDefaultAuthorizationType(node) {
        const resource = (0, ast_js_1.getUniqueWriteUsageOrNode)(ctx, node);
        if (defaultAuthorizationTypes.has(resource)) {
            return defaultAuthorizationTypes.get(resource);
        }
        else if (isDefaultFromCallee(resource)) {
            return getDefaultAuthorizationType(resource.callee);
        }
        else if (isDefaultFromObject(resource, ADD_METHOD, ADD_RESOURCE, REST_API_ROOT_PROPERTY)) {
            return getDefaultAuthorizationType(resource.object);
        }
        else {
            return undefined;
        }
    }
    function defaultsCollector(position) {
        return (expr) => {
            const properties = (0, result_js_1.getResultOfExpression)(ctx, expr).getArgument(position);
            const defaultMethodOptions = properties.getProperty(DEFAULT_METHOD_OPTIONS);
            const authorizationType = defaultMethodOptions.getProperty(AUTHORIZATION_TYPE);
            if (authorizationType.isFound) {
                defaultAuthorizationTypes.set(expr, authorizationType.node);
            }
        };
    }
    function isSensitiveAuthorizationType(node) {
        const fqn = (0, cdk_js_1.normalizeFQN)((0, module_js_1.getFullyQualifiedName)(ctx, node));
        return fqn === NONE_AUTHORIZATION_TYPE;
    }
}
function isDefaultFromObject(node, ...names) {
    return node.type === 'MemberExpression' && names.some(name => (0, ast_js_1.isMemberWithProperty)(node, name));
}
function isDefaultFromCallee(node) {
    return node.type === 'CallExpression' && (0, ast_js_1.isMethodCall)(node);
}
exports.rule = (0, cdk_js_1.AwsCdkTemplate)(consumersFactory, (0, generate_meta_js_1.generateMeta)(meta, { messages }));
