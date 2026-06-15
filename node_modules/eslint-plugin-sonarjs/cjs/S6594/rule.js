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
// https://sonarsource.github.io/rspec/#/rspec/S6594/javascript
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
const ancestor_js_1 = require("../helpers/ancestor.js");
const ast_js_1 = require("../helpers/ast.js");
const parser_services_js_1 = require("../helpers/parser-services.js");
const type_js_1 = require("../helpers/type.js");
const meta = __importStar(require("./generated-meta.js"));
const extract_js_1 = require("../helpers/regex/extract.js");
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        hasSuggestions: true,
        messages: {
            useExec: 'Use the "RegExp.exec()" method instead.',
            suggestExec: 'Replace with "RegExp.exec()"',
        },
    }),
    create(context) {
        const services = context.sourceCode.parserServices;
        if (!(0, parser_services_js_1.isRequiredParserServices)(services)) {
            return {};
        }
        return {
            "CallExpression[arguments.length=1] > MemberExpression.callee[property.name='match'][computed=false]": (memberExpr) => {
                const { object, property } = memberExpr;
                if (!(0, type_js_1.isString)(object, services)) {
                    return;
                }
                const callExpr = memberExpr.parent;
                const regex = (0, extract_js_1.getParsedRegex)(callExpr.arguments[0], context);
                if (regex?.flags.global) {
                    return;
                }
                const variable = getLhsVariable(callExpr);
                for (const ref of variable?.references ?? []) {
                    const id = ref.identifier;
                    const parent = (0, ancestor_js_1.getNodeParent)(id);
                    if ((0, ast_js_1.isMemberWithProperty)(parent, 'length')) {
                        return;
                    }
                }
                context.report({
                    node: property,
                    messageId: 'useExec',
                    suggest: [
                        {
                            messageId: 'suggestExec',
                            fix(fixer) {
                                const strText = context.sourceCode.getText(object);
                                const regText = context.sourceCode.getText(callExpr.arguments[0]);
                                const code = `RegExp(${regText}).exec(${strText})`;
                                return fixer.replaceText(callExpr, code);
                            },
                        },
                    ],
                });
            },
        };
        /**
         * Extracts the left-hand side variable of expressions
         * like `x` in `const x = <node>` or `x` in `x = <node>`.
         */
        function getLhsVariable(node) {
            const parent = (0, ancestor_js_1.getNodeParent)(node);
            let ident;
            if (parent.type === 'VariableDeclarator' && parent.id.type === 'Identifier') {
                ident = parent.id;
            }
            else if (parent.type === 'AssignmentExpression' && parent.left.type === 'Identifier') {
                ident = parent.left;
            }
            if (ident) {
                return (0, ast_js_1.getVariableFromName)(context, ident.name, node);
            }
            return null;
        }
    },
};
