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
// https://sonarsource.github.io/rspec/#/rspec/S5122/javascript
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
const location_js_1 = require("../helpers/location.js");
const meta = __importStar(require("./generated-meta.js"));
const MESSAGE = `Make sure that enabling CORS is safe here.`;
const SECONDARY_MESSAGE = 'Sensitive configuration';
const ACCESS_CONTROL_ALLOW_ORIGIN = 'Access-Control-Allow-Origin';
const ROUTINE_METHODS = new Set([
    'all', // 'all' is a special method that matches any HTTP method
    'checkout',
    'copy',
    'delete',
    'get',
    'head',
    'lock',
    'merge',
    'mkactivity',
    'mkcol',
    'move',
    'm-search',
    'notify',
    'options',
    'patch',
    'post',
    'purge',
    'put',
    'report',
    'search',
    'subscribe',
    'trace',
    'unlock',
    'unsubscribe',
]);
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta),
    create(context) {
        return {
            CallExpression(node) {
                checkNodeHttp(context, node);
                checkExpressCors(context, node);
                checkExpressUserControlledOrigin(context, node);
            },
        };
    },
};
/**
 * Checks that the callback of http.createServer() does not set the 'Access-Control-Allow-Origin' header to '*'.
 */
function checkNodeHttp(context, node) {
    // Check if the node is a call to the 'http.createServer' method
    const fqn = (0, module_js_1.getFullyQualifiedName)(context, node.callee);
    if (fqn !== 'http.createServer') {
        return;
    }
    // Check if the first argument is defined
    const arg0 = node.arguments[0];
    if (!arg0) {
        return;
    }
    // Check if the first argument is a callback function
    const callback = (0, ast_js_1.resolveFunction)(context, arg0);
    if (!callback) {
        return;
    }
    // Check if the callback has a response parameter
    const resParameter = callback.params[1];
    if (!resParameter || !(0, ast_js_1.isIdentifier)(resParameter)) {
        return;
    }
    // Retrieve the variable declaration of the response parameter
    const resVariable = context.sourceCode.scopeManager
        .getDeclaredVariables(callback)
        .find(v => v.name === resParameter.name);
    if (!resVariable) {
        return;
    }
    // Check if the response parameter is used to set the 'Access-Control-Allow-Origin' header
    const resUsages = resVariable.references;
    for (const resUsage of resUsages) {
        const identifier = resUsage.identifier;
        // Find the first ancestor that is a call to the 'writeHead' method
        const writeHeadCall = identifier?.parent?.parent;
        if (!(writeHeadCall?.type === 'CallExpression' && (0, ast_js_1.isCallingMethod)(writeHeadCall, 2, 'writeHead'))) {
            continue;
        }
        // Check if the header argument of the 'writeHead' method is defined
        const headerValue = (0, ast_js_1.getValueOfExpression)(context, writeHeadCall.arguments[1], 'ObjectExpression');
        if (!headerValue) {
            continue;
        }
        // Check if the header argument contains the 'Access-Control-Allow-Origin' property
        const accessProperty = (0, ast_js_1.getProperty)(headerValue, ACCESS_CONTROL_ALLOW_ORIGIN, context);
        if (!accessProperty) {
            continue;
        }
        // Check if the 'Access-Control-Allow-Origin' property is set to '*'
        const accessValue = (0, ast_js_1.getValueOfExpression)(context, accessProperty.value, 'Literal');
        if (accessValue?.value === '*') {
            (0, location_js_1.report)(context, {
                node: writeHeadCall.callee,
                message: MESSAGE,
            }, [(0, location_js_1.toSecondaryLocation)(accessProperty, SECONDARY_MESSAGE)]);
        }
    }
}
/**
 * Checks that the callback of express.use() does not use cors() middleware with sensitive configuration.
 */
function checkExpressCors(context, node) {
    // Check if the node is a call to the 'express.use' method
    const fqn = (0, module_js_1.getFullyQualifiedName)(context, node.callee);
    if (fqn !== 'express.use') {
        return;
    }
    // Check if the first argument is defined
    const argValue = (0, ast_js_1.getValueOfExpression)(context, node.arguments[0], 'CallExpression');
    if (!argValue) {
        return;
    }
    // Check if the first argument is a call to the 'cors' method
    const argFqn = (0, module_js_1.getFullyQualifiedName)(context, argValue);
    if (argFqn !== 'cors') {
        return;
    }
    // Check if the call to the 'cors' method has an argument (default configuration is sensitive)
    const corsOptions = argValue.arguments[0];
    if (!corsOptions) {
        (0, location_js_1.report)(context, {
            node,
            message: MESSAGE,
        });
        return;
    }
    // Check if the argument of the 'cors' method is an object
    const corsOptionsValue = (0, ast_js_1.getValueOfExpression)(context, corsOptions, 'ObjectExpression');
    if (!corsOptionsValue) {
        return;
    }
    // Check if the 'origin' property is defined  (default configuration is sensitive)
    const originProperty = (0, ast_js_1.getProperty)(corsOptionsValue, 'origin', context);
    if (!originProperty) {
        (0, location_js_1.report)(context, {
            node: node.callee,
            message: MESSAGE,
        }, [(0, location_js_1.toSecondaryLocation)(corsOptions, SECONDARY_MESSAGE)]);
        return;
    }
    // Check if the 'origin' property is set to '*'
    const originValue = (0, ast_js_1.getValueOfExpression)(context, originProperty.value, 'Literal');
    if (originValue?.value === '*') {
        (0, location_js_1.report)(context, {
            node: node.callee,
            message: MESSAGE,
        }, [(0, location_js_1.toSecondaryLocation)(originProperty, SECONDARY_MESSAGE)]);
    }
}
/**
 * Checks that the callback of express.<method>() does not set the 'Access-Control-Allow-Origin' header to '*'.
 */
function checkExpressUserControlledOrigin(context, node) {
    // Check if the node is a call to an express routine method
    const fqn = (0, module_js_1.getFullyQualifiedName)(context, node.callee)?.split('.');
    if (!(fqn?.length === 2 && fqn[0] === 'express' && ROUTINE_METHODS.has(fqn[1]))) {
        return;
    }
    // Check if the second argument is defined
    const arg1 = node.arguments[1];
    if (!arg1) {
        return;
    }
    // Check if the second argument is a callback function
    const callback = (0, ast_js_1.resolveFunction)(context, arg1);
    if (!callback) {
        return;
    }
    // Check if the callback has a request parameter
    const reqParameter = callback.params[0];
    if (!reqParameter || !(0, ast_js_1.isIdentifier)(reqParameter)) {
        return;
    }
    // Check if the callback has a response parameter
    const resParameter = callback.params[1];
    if (!resParameter || !(0, ast_js_1.isIdentifier)(resParameter)) {
        return;
    }
    // Retrieve the variable declaration of the response parameter
    const resVariable = context.sourceCode.scopeManager
        .getDeclaredVariables(callback)
        .find(v => v.name === resParameter.name);
    if (!resVariable) {
        return;
    }
    // Check if the response parameter is used to set the 'Access-Control-Allow-Origin' header
    const resUsages = resVariable.references;
    for (const resUsage of resUsages) {
        const identifier = resUsage.identifier;
        // Find the first ancestor that is a call to the 'setHeader' method
        const setHeaderCall = identifier?.parent?.parent;
        if (!(setHeaderCall?.type === 'CallExpression' && (0, ast_js_1.isCallingMethod)(setHeaderCall, 2, 'setHeader'))) {
            continue;
        }
        // Check if the first argument of the 'setHeader' method is 'Access-Control-Allow-Origin'
        const headerName = (0, ast_js_1.getValueOfExpression)(context, setHeaderCall.arguments[0], 'Literal');
        if (!headerName ||
            typeof headerName.value !== 'string' ||
            headerName.value.toLowerCase() !== ACCESS_CONTROL_ALLOW_ORIGIN.toLowerCase()) {
            continue;
        }
        // Retrieve the value of the header argument
        const headerArg = setHeaderCall.arguments[1];
        const headerValue = (0, ast_js_1.getUniqueWriteUsageOrNode)(context, headerArg);
        // Check if the header value is a user-controlled origin header
        switch (headerValue.type) {
            // Check if the header value is a call to the 'req.header' method with 'origin' as argument
            case 'CallExpression': {
                const callee = headerValue.callee;
                const calleeText = context.sourceCode.getText(callee);
                if (calleeText === `${reqParameter.name}.header`) {
                    const originValue = (0, ast_js_1.getValueOfExpression)(context, headerValue.arguments[0], 'Literal');
                    if (typeof originValue?.value === 'string' &&
                        originValue.value.toLowerCase() === 'origin' &&
                        !isValidated(callback, headerArg)) {
                        (0, location_js_1.report)(context, {
                            node: setHeaderCall.callee,
                            message: MESSAGE,
                        }, [(0, location_js_1.toSecondaryLocation)(headerValue, SECONDARY_MESSAGE)]);
                    }
                }
                break;
            }
            // Check if the header value is a member expression with 'req.headers.origin' as argument
            case 'MemberExpression': {
                const headerValueText = context.sourceCode.getText(headerValue);
                if (headerValueText === `${reqParameter.name}.headers.origin` &&
                    !isValidated(callback, headerArg)) {
                    (0, location_js_1.report)(context, {
                        node: setHeaderCall.callee,
                        message: MESSAGE,
                    }, [(0, location_js_1.toSecondaryLocation)(headerValue, SECONDARY_MESSAGE)]);
                }
                break;
            }
        }
    }
    /**
     * Checks if the user-controlled origin header is validated in the callback through a comparison.
     */
    function isValidated(callback, header) {
        if (!(0, ast_js_1.isIdentifier)(header)) {
            return false;
        }
        // Find the variable declaration of the header
        const headerVariable = context.sourceCode.scopeManager
            .acquire(callback)
            ?.variables.find(v => v.name === header.name);
        if (!headerVariable) {
            return false;
        }
        // Check if the header is compared in a binary expression
        const headerUsages = headerVariable.references;
        for (const headerUsage of headerUsages) {
            const identifier = headerUsage.identifier;
            const validated = (0, ancestor_js_1.findFirstMatchingLocalAncestor)(identifier, node => node.type === 'BinaryExpression' && ['==', '!=', '===', '!=='].includes(node.operator));
            if (validated) {
                return true;
            }
        }
        return false;
    }
}
