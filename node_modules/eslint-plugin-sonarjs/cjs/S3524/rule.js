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
// https://sonarsource.github.io/rspec/#/rspec/S3524/javascript
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
const meta = __importStar(require("./generated-meta.js"));
const MESSAGE_ADD_PARAMETER = 'Add parentheses around the parameter of this arrow function.';
const MESSAGE_REMOVE_PARAMETER = 'Remove parentheses around the parameter of this arrow function.';
const MESSAGE_ADD_BODY = 'Add curly braces and "return" to this arrow function body.';
const MESSAGE_REMOVE_BODY = 'Remove curly braces and "return" from this arrow function body.';
const DEFAULT_OPTIONS = {
    requireParameterParentheses: false,
    requireBodyBraces: false,
};
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta),
    create(context) {
        const { requireParameterParentheses, requireBodyBraces } = {
            ...DEFAULT_OPTIONS,
            ...context.options[0],
        };
        return {
            ArrowFunctionExpression(node) {
                const arrowFunction = node;
                checkParameters(context, requireParameterParentheses, arrowFunction);
                checkBody(context, requireBodyBraces, arrowFunction);
            },
        };
    },
};
function checkParameters(context, requireParameterParentheses, arrowFunction) {
    if (arrowFunction.params.length !== 1) {
        return;
    }
    const parameter = arrowFunction.params[0];
    // Looking at the closing parenthesis after the parameter to avoid problems with cases like
    // `functionTakingCallbacks(x => {...})` where the opening parenthesis before `x` isn't part
    // of the function literal
    const tokenAfterParameter = context.sourceCode.getTokenAfter(parameter);
    const hasParameterParentheses = tokenAfterParameter?.value === ')';
    if (requireParameterParentheses && !hasParameterParentheses) {
        context.report({ node: parameter, message: MESSAGE_ADD_PARAMETER });
    }
    else if (!requireParameterParentheses &&
        !hasGeneric(context, arrowFunction) &&
        hasParameterParentheses) {
        const arrowFunctionComments = context.sourceCode.getCommentsInside(arrowFunction);
        const arrowFunctionBodyComments = context.sourceCode.getCommentsInside(arrowFunction.body);
        // parameters comments inside parentheses are not available, so use the following subtraction:
        const hasArrowFunctionParamsComments = arrowFunctionComments.some(comment => !arrowFunctionBodyComments.includes(comment));
        if (parameter.type === 'Identifier' &&
            !hasArrowFunctionParamsComments &&
            !parameter.typeAnnotation &&
            !arrowFunction.returnType) {
            context.report({ node: parameter, message: MESSAGE_REMOVE_PARAMETER });
        }
    }
}
function hasGeneric(context, arrowFunction) {
    const offset = arrowFunction.async ? 1 : 0;
    const firstTokenIgnoreAsync = context.sourceCode.getFirstToken(arrowFunction, offset);
    return firstTokenIgnoreAsync?.value === '<';
}
function checkBody(context, requireBodyBraces, arrowFunction) {
    const hasBodyBraces = arrowFunction.body.type === 'BlockStatement';
    if (requireBodyBraces && !hasBodyBraces) {
        context.report({ node: arrowFunction.body, message: MESSAGE_ADD_BODY });
    }
    else if (!requireBodyBraces && hasBodyBraces) {
        const statements = arrowFunction.body.body;
        if (statements.length === 1) {
            const statement = statements[0];
            if (isRemovableReturn(statement)) {
                context.report({ node: arrowFunction.body, message: MESSAGE_REMOVE_BODY });
            }
        }
    }
}
function isRemovableReturn(statement) {
    if (statement.type === 'ReturnStatement') {
        const returnStatement = statement;
        const returnExpression = returnStatement.argument;
        if (returnExpression && returnExpression.type !== 'ObjectExpression') {
            const location = returnExpression.loc;
            return location && location.start.line === location.end.line;
        }
    }
    return false;
}
