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
// https://sonarsource.github.io/rspec/#/rspec/S3782/javascript
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
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const type_js_1 = require("../helpers/type.js");
const parser_services_js_1 = require("../helpers/parser-services.js");
const typescript_1 = __importDefault(require("typescript"));
const meta = __importStar(require("./generated-meta.js"));
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta),
    create(context) {
        const services = context.sourceCode.parserServices;
        if (!(0, parser_services_js_1.isRequiredParserServices)(services)) {
            return {};
        }
        const tc = services.program.getTypeChecker();
        function isBuiltInMethod(symbol) {
            const parent = symbol.valueDeclaration?.parent;
            if (parent?.kind !== typescript_1.default.SyntaxKind.InterfaceDeclaration) {
                return false;
            }
            const parentSymbol = tc.getSymbolAtLocation(parent.name);
            if (!parentSymbol) {
                return false;
            }
            const fqn = tc.getFullyQualifiedName(parentSymbol);
            // some of the built-in objects are deliberately excluded, because they generate many FPs
            // and no relevant TP, e.g. RegExp, Function
            return ['String', 'Math', 'Array', 'Number', 'Date'].includes(fqn);
        }
        function declarationMismatch(declaration, callExpression) {
            const parameters = declaration.parameters;
            for (let i = 0; i < Math.min(parameters.length, callExpression.arguments.length); i++) {
                const parameterType = parameters[i].type;
                if (!parameterType) {
                    return null;
                }
                const declaredType = tc.getTypeFromTypeNode(parameterType);
                const actualType = (0, type_js_1.getTypeFromTreeNode)(callExpression.arguments[i], services);
                if (
                // @ts-ignore private API, see https://github.com/microsoft/TypeScript/issues/9879
                !tc.isTypeAssignableTo(actualType, declaredType) &&
                    !isTypeParameter(declaredType) &&
                    !typescript_1.default.isFunctionTypeNode(parameterType) &&
                    !isVarArg(parameters[i])) {
                    return { actualType, declaredType, node: callExpression.arguments[i] };
                }
            }
            return null;
        }
        function typeToString(type) {
            return tc.typeToString(tc.getBaseTypeOfLiteralType(type));
        }
        return {
            CallExpression: (node) => {
                const callExpression = node;
                const tsCallExpr = services.esTreeNodeToTSNodeMap.get(callExpression.callee);
                const symbol = tc.getSymbolAtLocation(tsCallExpr);
                if (symbol?.declarations && isBuiltInMethod(symbol)) {
                    let mismatch = null;
                    for (const declaration of symbol.declarations) {
                        mismatch = declarationMismatch(declaration, callExpression);
                        if (!mismatch) {
                            return;
                        }
                    }
                    if (mismatch) {
                        context.report({
                            node: mismatch.node,
                            message: `Verify that argument is of correct type: expected '${typeToString(mismatch.declaredType)}' instead of '${typeToString(mismatch.actualType)}'.`,
                        });
                    }
                }
            },
        };
    },
};
function isVarArg(param) {
    return !!param.dotDotDotToken;
}
function isTypeParameter(type) {
    return type.getFlags() & typescript_1.default.TypeFlags.TypeParameter;
}
