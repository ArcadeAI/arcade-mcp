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
// https://sonarsource.github.io/rspec/#/rspec/S5247/javascript
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
const parser_services_js_1 = require("../helpers/parser-services.js");
const location_js_1 = require("../helpers/location.js");
const meta = __importStar(require("./generated-meta.js"));
const MESSAGE = 'Make sure disabling auto-escaping feature is safe here.';
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta),
    create(context) {
        const services = context.sourceCode.parserServices;
        function isInvalidSanitizerFunction(node) {
            let assignedFunction = (0, ast_js_1.getValueOfExpression)(context, node, 'FunctionExpression') ??
                (0, ast_js_1.getValueOfExpression)(context, node, 'ArrowFunctionExpression');
            if (!assignedFunction && node.type === 'Identifier' && (0, parser_services_js_1.isRequiredParserServices)(services)) {
                assignedFunction = (0, ast_js_1.resolveFromFunctionReference)(context, node);
            }
            if (assignedFunction) {
                return isEmptySanitizerFunction(assignedFunction);
            }
            return false;
        }
        return {
            CallExpression: (node) => {
                const callExpression = node;
                const fqn = (0, module_js_1.getFullyQualifiedName)(context, callExpression);
                if (fqn === 'handlebars.compile') {
                    (0, ast_js_1.checkSensitiveCall)(context, callExpression, 1, 'noEscape', true, MESSAGE);
                }
                if (fqn === 'marked.setOptions') {
                    (0, ast_js_1.checkSensitiveCall)(context, callExpression, 0, 'sanitize', false, MESSAGE);
                }
                if (fqn === 'markdown-it') {
                    (0, ast_js_1.checkSensitiveCall)(context, callExpression, 0, 'html', true, MESSAGE);
                }
                if (fqn === 'swig.setDefaults') {
                    (0, ast_js_1.checkSensitiveCall)(context, callExpression, 0, 'autoescape', false, MESSAGE);
                }
            },
            NewExpression: (node) => {
                const newExpression = node;
                if ((0, module_js_1.getFullyQualifiedName)(context, newExpression) === 'kramed.Renderer') {
                    (0, ast_js_1.checkSensitiveCall)(context, newExpression, 0, 'sanitize', false, MESSAGE);
                }
            },
            AssignmentExpression: (node) => {
                const assignmentExpression = node;
                const { left, right } = assignmentExpression;
                if (left.type !== 'MemberExpression') {
                    return;
                }
                if (!((0, module_js_1.getFullyQualifiedName)(context, left) === 'mustache.escape' ||
                    (isMustacheIdentifier(left.object) && (0, ast_js_1.isIdentifier)(left.property, 'escape')))) {
                    return;
                }
                if (isInvalidSanitizerFunction(right)) {
                    (0, location_js_1.report)(context, {
                        node: left,
                        message: MESSAGE,
                    });
                }
            },
        };
    },
};
function isEmptySanitizerFunction(sanitizerFunction) {
    if (sanitizerFunction.params.length !== 1) {
        return false;
    }
    const firstParam = sanitizerFunction.params[0];
    if (firstParam.type !== 'Identifier') {
        return false;
    }
    const firstParamName = firstParam.name;
    if (sanitizerFunction.body.type !== 'BlockStatement') {
        return (sanitizerFunction.body.type === 'Identifier' && sanitizerFunction.body.name === firstParamName);
    }
    const { body } = sanitizerFunction.body;
    if (body.length !== 1) {
        return false;
    }
    const onlyStatement = body[0];
    return !!(onlyStatement.type === 'ReturnStatement' &&
        onlyStatement.argument &&
        (0, ast_js_1.isIdentifier)(onlyStatement.argument, firstParamName));
}
function isMustacheIdentifier(node) {
    return (0, ast_js_1.isIdentifier)(node, 'Mustache');
}
