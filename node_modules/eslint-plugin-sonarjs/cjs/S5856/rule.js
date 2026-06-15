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
// https://sonarsource.github.io/rspec/#/rspec/S5856/javascript
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
const type_js_1 = require("../helpers/type.js");
const ast_js_1 = require("../helpers/ast.js");
const parser_services_js_1 = require("../helpers/parser-services.js");
const regexpp_1 = require("@eslint-community/regexpp");
const meta = __importStar(require("./generated-meta.js"));
const validator = new regexpp_1.RegExpValidator();
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta),
    create(context) {
        function isStringMatch(call) {
            const services = context.sourceCode.parserServices;
            if (!(0, parser_services_js_1.isRequiredParserServices)(services)) {
                return false;
            }
            const { callee } = call;
            return (callee.type === 'MemberExpression' &&
                (0, type_js_1.isStringType)((0, type_js_1.getTypeFromTreeNode)(callee.object, services)) &&
                (0, ast_js_1.isIdentifier)(callee.property, 'match'));
        }
        return {
            'CallExpression, NewExpression'(node) {
                const call = node;
                if (!isRegExpConstructor(call) && !isStringMatch(call)) {
                    return;
                }
                const pattern = getPattern(call);
                if (!pattern) {
                    return;
                }
                const flags = getFlags(call);
                const message = (flags && validateRegExpFlags(flags)) ||
                    // If flags are unknown, report the regex only if its pattern is invalid both with and without the "u" flag
                    (flags === null
                        ? validateRegExpPattern(pattern, true) && validateRegExpPattern(pattern, false)
                        : validateRegExpPattern(pattern, flags.includes('u')));
                if (message) {
                    context.report({
                        node,
                        message,
                    });
                }
            },
        };
    },
};
function getFlags(node) {
    if (node.arguments.length < 2) {
        return '';
    }
    if ((0, ast_js_1.isStringLiteral)(node.arguments[1])) {
        return node.arguments[1].value;
    }
    return null;
}
function validateRegExpPattern(pattern, uFlag) {
    try {
        validator.validatePattern(pattern, undefined, undefined, uFlag);
        return null;
    }
    catch (err) {
        return err.message;
    }
}
function validateRegExpFlags(flags) {
    try {
        validator.validateFlags(flags);
        return null;
    }
    catch {
        return `Invalid flags supplied to RegExp constructor '${flags}'`;
    }
}
function isRegExpConstructor(call) {
    const { callee } = call;
    return callee.type === 'Identifier' && callee.name === 'RegExp';
}
function getPattern(call) {
    if ((0, ast_js_1.isStringLiteral)(call.arguments[0])) {
        return call.arguments[0].value;
    }
    return null;
}
