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
// https://sonarsource.github.io/rspec/#/rspec/S3796/javascript
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
const parser_services_js_1 = require("../helpers/parser-services.js");
const type_js_1 = require("../helpers/type.js");
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const location_js_1 = require("../helpers/location.js");
const ast_js_1 = require("../helpers/ast.js");
const meta = __importStar(require("./generated-meta.js"));
const message = `Add a "return" statement to this callback.`;
const methodsWithCallback = new Set([
    'every',
    'filter',
    'find',
    'findLast',
    'findIndex',
    'findLastIndex',
    'map',
    'flatMap',
    'reduce',
    'reduceRight',
    'some',
    'sort',
    'toSorted',
]);
function hasCallBackWithoutReturn(argument, services) {
    const checker = services.program.getTypeChecker();
    const type = checker.getTypeAtLocation(services.esTreeNodeToTSNodeMap.get(argument));
    const signatures = type.getCallSignatures();
    return (signatures.length > 0 &&
        signatures.every(sig => checker.typeToString(sig.getReturnType()) === 'void'));
}
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta),
    create(context) {
        const services = context.sourceCode.parserServices;
        if (!(0, parser_services_js_1.isRequiredParserServices)(services)) {
            return {};
        }
        return {
            'CallExpression[callee.type="MemberExpression"]'(node) {
                const callExpression = node;
                const args = callExpression.arguments;
                const memberExpression = callExpression.callee;
                const { object } = memberExpression;
                const propName = extractPropName(memberExpression);
                if (propName === null || args.length === 0) {
                    return;
                }
                if (methodsWithCallback.has(propName) &&
                    ((0, type_js_1.isArray)(object, services) || (0, type_js_1.isTypedArray)(object, services)) &&
                    hasCallBackWithoutReturn(args[0], services)) {
                    context.report({
                        message,
                        ...getNodeToReport(args[0], node, context),
                    });
                }
                else if ((0, ast_js_1.isMemberExpression)(callExpression.callee, 'Array', 'from') &&
                    args.length > 1 &&
                    hasCallBackWithoutReturn(args[1], services)) {
                    context.report({
                        message,
                        ...getNodeToReport(args[1], node, context),
                    });
                }
            },
        };
    },
};
function extractPropName(memberExpression) {
    if ((0, ast_js_1.isDotNotation)(memberExpression)) {
        return memberExpression.property.name;
    }
    else if ((0, ast_js_1.isIndexNotation)(memberExpression)) {
        return memberExpression.property.value;
    }
    else {
        return null;
    }
}
function getNodeToReport(node, parent, context) {
    if (node.type === 'FunctionDeclaration' ||
        node.type === 'FunctionExpression' ||
        node.type === 'ArrowFunctionExpression') {
        return {
            loc: (0, location_js_1.getMainFunctionTokenLocation)(node, parent, context),
        };
    }
    return {
        node,
    };
}
