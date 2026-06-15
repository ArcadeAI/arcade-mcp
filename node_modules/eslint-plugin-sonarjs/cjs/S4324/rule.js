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
// https://sonarsource.github.io/rspec/#/rspec/S4324/javascript
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
const collection_js_1 = require("../helpers/collection.js");
const typescript_1 = __importDefault(require("typescript"));
const meta = __importStar(require("./generated-meta.js"));
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            removeOrChangeType: 'Remove this return type or change it to a more specific.',
        },
    }),
    create(context) {
        const services = context.sourceCode.parserServices;
        if ((0, parser_services_js_1.isRequiredParserServices)(services)) {
            const returnedExpressions = [];
            return {
                ReturnStatement(node) {
                    if (returnedExpressions.length > 0) {
                        (0, collection_js_1.last)(returnedExpressions).push(node.argument);
                    }
                },
                FunctionDeclaration() {
                    returnedExpressions.push([]);
                },
                'FunctionDeclaration:exit'(node) {
                    const returnType = node.returnType;
                    if (returnType?.typeAnnotation.type === 'TSAnyKeyword' &&
                        returnedExpressions.length > 0 &&
                        allReturnTypesEqual((0, collection_js_1.last)(returnedExpressions), services)) {
                        context.report({
                            messageId: 'removeOrChangeType',
                            loc: returnType.loc,
                        });
                    }
                    returnedExpressions.pop();
                },
            };
        }
        return {};
    },
};
function allReturnTypesEqual(returns, services) {
    const firstReturnType = getTypeFromTreeNode(returns.pop(), services);
    if (!!firstReturnType && !!isPrimitiveType(firstReturnType)) {
        return returns.every(nextReturn => {
            const nextReturnType = getTypeFromTreeNode(nextReturn, services);
            return !!nextReturnType && nextReturnType.flags === firstReturnType.flags;
        });
    }
    return false;
}
function getTypeFromTreeNode(node, services) {
    const checker = services.program.getTypeChecker();
    return checker.getTypeAtLocation(services.esTreeNodeToTSNodeMap.get(node));
}
function isPrimitiveType({ flags }) {
    return (flags & typescript_1.default.TypeFlags.BooleanLike ||
        flags & typescript_1.default.TypeFlags.NumberLike ||
        flags & typescript_1.default.TypeFlags.StringLike ||
        flags & typescript_1.default.TypeFlags.EnumLike);
}
