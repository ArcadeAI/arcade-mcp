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
// https://sonarsource.github.io/rspec/#/rspec/S2201
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
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.rule = void 0;
const typescript_1 = __importDefault(require("typescript"));
const ancestor_js_1 = require("../helpers/ancestor.js");
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const type_js_1 = require("../helpers/type.js");
const parser_services_js_1 = require("../helpers/parser-services.js");
const meta = __importStar(require("./generated-meta.js"));
const METHODS_WITHOUT_SIDE_EFFECTS = {
    array: new Set([
        'concat',
        'includes',
        'join',
        'slice',
        'indexOf',
        'lastIndexOf',
        'entries',
        'filter',
        'findIndex',
        'findLast',
        'findLastIndex',
        'keys',
        'map',
        'values',
        'find',
        'reduce',
        'reduceRight',
        'toString',
        'toLocaleString',
    ]),
    date: new Set([
        'getDate',
        'getDay',
        'getFullYear',
        'getHours',
        'getMilliseconds',
        'getMinutes',
        'getMonth',
        'getSeconds',
        'getTime',
        'getTimezoneOffset',
        'getUTCDate',
        'getUTCDay',
        'getUTCFullYear',
        'getUTCHours',
        'getUTCMilliseconds',
        'getUTCMinutes',
        'getUTCMonth',
        'getUTCSeconds',
        'getYear',
        'toDateString',
        'toISOString',
        'toJSON',
        'toGMTString',
        'toLocaleDateString',
        'toLocaleTimeString',
        'toTimeString',
        'toUTCString',
        'toString',
        'toLocaleString',
    ]),
    math: new Set([
        'abs',
        'E',
        'LN2',
        'LN10',
        'LOG2E',
        'LOG10E',
        'PI',
        'SQRT1_2',
        'SQRT2',
        'abs',
        'acos',
        'acosh',
        'asin',
        'asinh',
        'atan',
        'atanh',
        'atan2',
        'cbrt',
        'ceil',
        'clz32',
        'cos',
        'cosh',
        'exp',
        'expm1',
        'floor',
        'fround',
        'hypot',
        'imul',
        'log',
        'log1p',
        'log10',
        'log2',
        'max',
        'min',
        'pow',
        'random',
        'round',
        'sign',
        'sin',
        'sinh',
        'sqrt',
        'tan',
        'tanh',
        'trunc',
    ]),
    number: new Set(['toExponential', 'toFixed', 'toPrecision', 'toLocaleString', 'toString']),
    regexp: new Set(['test', 'toString']),
    string: new Set([
        'charAt',
        'charCodeAt',
        'codePointAt',
        'concat',
        'includes',
        'endsWith',
        'indexOf',
        'lastIndexOf',
        'localeCompare',
        'match',
        'normalize',
        'padEnd',
        'padStart',
        'repeat',
        'replace',
        'search',
        'slice',
        'split',
        'startsWith',
        'substr',
        'substring',
        'toLocaleLowerCase',
        'toLocaleUpperCase',
        'toLowerCase',
        'toUpperCase',
        'trim',
        'length',
        'toString',
        'valueOf',
        // HTML wrapper methods
        'anchor',
        'big',
        'blink',
        'bold',
        'fixed',
        'fontcolor',
        'fontsize',
        'italics',
        'link',
        'small',
        'strike',
        'sub',
        'sup',
    ]),
};
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            useForEach: `Consider using "forEach" instead of "map" as its return value is not being used here.`,
            returnValueMustBeUsed: 'The return value of "{{methodName}}" must be used.',
        },
    }),
    create(context) {
        const services = context.sourceCode.parserServices;
        if (!(0, parser_services_js_1.isRequiredParserServices)(services)) {
            return {};
        }
        return {
            CallExpression: (node) => {
                const call = node;
                const { callee } = call;
                if (callee.type === 'MemberExpression') {
                    const { parent } = node;
                    if (parent?.type === 'ExpressionStatement') {
                        const methodName = context.sourceCode.getText(callee.property);
                        const objectType = services.program
                            .getTypeChecker()
                            .getTypeAtLocation(services.esTreeNodeToTSNodeMap.get(callee.object));
                        if (!hasSideEffect(methodName, objectType, services) &&
                            !isReplaceWithCallback(methodName, call.arguments, services) &&
                            !isFindWithAssignmentCallback(methodName, call.arguments, context.sourceCode.visitorKeys)) {
                            context.report(reportDescriptor(methodName, node));
                        }
                    }
                }
            },
        };
    },
};
const FunctionTypeNodeKind = typescript_1.default.SyntaxKind.FunctionType;
const isFunctionTypeNode = (candidate) => {
    return candidate.kind === FunctionTypeNodeKind;
};
function isReplaceWithCallback(methodName, callArguments, services) {
    if (methodName === 'replace' && callArguments.length > 1) {
        const type = (0, type_js_1.getTypeFromTreeNode)(callArguments[1], services);
        const typeNode = services.program.getTypeChecker().typeToTypeNode(type, undefined, undefined);
        return typeNode && isFunctionTypeNode(typeNode);
    }
    return false;
}
// Early-exit array methods currently in METHODS_WITHOUT_SIDE_EFFECTS['array']
const EARLY_EXIT_ARRAY_METHODS = new Set(['find', 'findIndex', 'findLast', 'findLastIndex']);
/**
 * Returns true if the call is an early-exit array method whose first argument is an inline
 * function containing an AssignmentExpression. Such callbacks intentionally assign to outer
 * variables to exploit early-exit behavior, making the return value unused by design.
 */
function isFindWithAssignmentCallback(methodName, callArguments, visitorKeys) {
    if (!EARLY_EXIT_ARRAY_METHODS.has(methodName) || callArguments.length === 0) {
        return false;
    }
    const callback = callArguments[0];
    if (callback.type !== 'ArrowFunctionExpression' && callback.type !== 'FunctionExpression') {
        return false;
    }
    return containsAssignment(callback.body, visitorKeys);
}
const FUNCTION_BOUNDARIES = new Set([
    'FunctionExpression',
    'ArrowFunctionExpression',
    'FunctionDeclaration',
]);
/**
 * Recursively checks if an AST node contains an AssignmentExpression, using childrenOf for
 * complete traversal. Stops at nested function boundaries so assignments in inner closures
 * do not suppress the issue.
 */
function containsAssignment(node, visitorKeys) {
    if (node.type === 'AssignmentExpression') {
        return true;
    }
    if (FUNCTION_BOUNDARIES.has(node.type)) {
        return false;
    }
    return (0, ancestor_js_1.childrenOf)(node, visitorKeys).some(child => containsAssignment(child, visitorKeys));
}
function reportDescriptor(methodName, node) {
    if (methodName === 'map') {
        return {
            messageId: 'useForEach',
            node,
        };
    }
    else {
        return {
            messageId: 'returnValueMustBeUsed',
            node,
            data: { methodName },
        };
    }
}
function hasSideEffect(methodName, objectType, services) {
    const typeAsString = typeToString(objectType, services);
    if (typeAsString !== null) {
        const methods = METHODS_WITHOUT_SIDE_EFFECTS[typeAsString];
        return !methods?.has(methodName);
    }
    return true;
}
function typeToString(tp, services) {
    const typechecker = services.program.getTypeChecker();
    const baseType = typechecker.getBaseTypeOfLiteralType(tp);
    const typeAsString = typechecker.typeToString(baseType);
    if (typeAsString === 'number' || typeAsString === 'string') {
        return typeAsString;
    }
    const symbol = tp.getSymbol();
    if (symbol) {
        const name = symbol.getName();
        switch (name) {
            case 'Array':
            case 'Date':
            case 'Math':
            case 'RegExp':
                return name.toLowerCase();
        }
    }
    return null;
}
