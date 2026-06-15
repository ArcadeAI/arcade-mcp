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
// https://sonarsource.github.io/rspec/#/rspec/S4623/javascript
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
const parser_services_js_1 = require("../helpers/parser-services.js");
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const ast_js_1 = require("../helpers/ast.js");
const collection_js_1 = require("../helpers/collection.js");
const typescript_1 = __importDefault(require("typescript"));
const meta = __importStar(require("./generated-meta.js"));
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        hasSuggestions: true,
        messages: {
            removeUndefined: 'Remove this redundant "undefined".',
            suggestRemoveUndefined: 'Remove this redundant argument',
        },
    }),
    create(context) {
        const services = context.sourceCode.parserServices;
        if ((0, parser_services_js_1.isRequiredParserServices)(services)) {
            return {
                CallExpression: (node) => {
                    const call = node;
                    const { arguments: args } = call;
                    if (args.length === 0) {
                        return;
                    }
                    const lastArgument = (0, collection_js_1.last)(args);
                    if ((0, ast_js_1.isUndefined)(lastArgument) && isOptionalParameter(args.length - 1, call, services)) {
                        context.report({
                            messageId: 'removeUndefined',
                            node: lastArgument,
                            suggest: [
                                {
                                    messageId: 'suggestRemoveUndefined',
                                    fix: fixer => {
                                        if (call.arguments.length === 1) {
                                            const openingParen = context.sourceCode.getTokenAfter(call.callee);
                                            const closingParen = context.sourceCode.getLastToken(node);
                                            const [, begin] = openingParen.range;
                                            const [end] = closingParen.range;
                                            return fixer.removeRange([begin, end]);
                                        }
                                        else {
                                            const [, begin] = args.at(-2).range;
                                            const [, end] = lastArgument.range;
                                            return fixer.removeRange([begin, end]);
                                        }
                                    },
                                },
                            ],
                        });
                    }
                },
            };
        }
        return {};
    },
};
function isOptionalParameter(paramIndex, node, services) {
    const signature = services.program
        .getTypeChecker()
        .getResolvedSignature(services.esTreeNodeToTSNodeMap.get(node));
    if (signature) {
        const declaration = signature.declaration;
        if (declaration && isFunctionLikeDeclaration(declaration)) {
            const { parameters } = declaration;
            const parameter = parameters[paramIndex];
            return parameter && (parameter.initializer || parameter.questionToken);
        }
    }
    return false;
}
function isFunctionLikeDeclaration(declaration) {
    return [
        typescript_1.default.SyntaxKind.FunctionDeclaration,
        typescript_1.default.SyntaxKind.FunctionExpression,
        typescript_1.default.SyntaxKind.ArrowFunction,
        typescript_1.default.SyntaxKind.MethodDeclaration,
        typescript_1.default.SyntaxKind.Constructor,
        typescript_1.default.SyntaxKind.GetAccessor,
        typescript_1.default.SyntaxKind.SetAccessor,
    ].includes(declaration.kind);
}
