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
// https://sonarsource.github.io/rspec/#/rspec/S4335/javascript
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
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const ancestor_js_1 = require("../helpers/ancestor.js");
const parser_services_js_1 = require("../helpers/parser-services.js");
const meta = __importStar(require("./generated-meta.js"));
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            removeIntersection: 'Remove this type without members or change this type intersection.',
            simplifyIntersection: 'Simplify this intersection as it always has type "{{type}}".',
        },
    }),
    create(context) {
        const services = context.sourceCode.parserServices;
        if (!(0, parser_services_js_1.isRequiredParserServices)(services)) {
            return {};
        }
        function checkIntersectionType(node) {
            const intersection = node;
            const anyOrNever = intersection.types.find(typeNode => ['TSAnyKeyword', 'TSNeverKeyword'].includes(typeNode.type));
            if (anyOrNever) {
                context.report({
                    messageId: 'simplifyIntersection',
                    data: {
                        type: anyOrNever.type === 'TSAnyKeyword' ? 'any' : 'never',
                    },
                    node,
                });
                return;
            }
            checkTypesWithoutMembers(intersection, services);
        }
        function checkTypesWithoutMembers(intersection, parserServices) {
            for (const typeNode of intersection.types) {
                const tp = parserServices.program
                    .getTypeChecker()
                    .getTypeAtLocation(parserServices.esTreeNodeToTSNodeMap.get(typeNode));
                if (!isTypeWithoutMembers(tp)) {
                    continue;
                }
                if (isLiteralUnionPattern(intersection)) {
                    continue;
                }
                if (isGenericTypePattern(intersection, typeNode, parserServices)) {
                    continue;
                }
                context.report({
                    messageId: 'removeIntersection',
                    node: typeNode,
                });
            }
        }
        return {
            TSIntersectionType: checkIntersectionType,
        };
    },
};
function isTypeWithoutMembers(tp) {
    return isNullLike(tp) || (isEmptyInterface(tp) && isStandaloneInterface(tp.symbol));
}
function isNullLike(tp) {
    return (Boolean(tp.flags & typescript_1.default.TypeFlags.Null) ||
        Boolean(tp.flags & typescript_1.default.TypeFlags.Undefined) ||
        Boolean(tp.flags & typescript_1.default.TypeFlags.Void));
}
function isEmptyInterface(tp) {
    return (tp.getProperties().length === 0 &&
        (!tp.declaredIndexInfos ||
            tp.declaredIndexInfos.length === 0));
}
function isStandaloneInterface(typeSymbol) {
    // there is no declarations for `{}`
    // otherwise check that none of declarations has a heritage clause (`extends X` or `implements X`)
    if (!typeSymbol) {
        return false;
    }
    const { declarations } = typeSymbol;
    return (!declarations ||
        declarations.every(declaration => {
            return (isInterfaceDeclaration(declaration) && (declaration.heritageClauses ?? []).length === 0);
        }));
}
function isInterfaceDeclaration(declaration) {
    return declaration.kind === typescript_1.default.SyntaxKind.InterfaceDeclaration;
}
/**
 * Detects the LiteralUnion pattern: `(X & {})` used within a union type to preserve
 * IDE autocomplete for literal types while accepting any primitive value.
 * Example: `'small' | 'medium' | 'large' | (string & {})`
 */
function isLiteralUnionPattern(intersection) {
    if (intersection.types.length !== 2) {
        return false;
    }
    const parent = (0, ancestor_js_1.getNodeParent)(intersection);
    if (!parent || parent.type !== 'TSUnionType') {
        return false;
    }
    const otherType = intersection.types.find(t => t.type !== 'TSTypeLiteral' || (t.members && t.members.length > 0));
    if (!otherType) {
        return false;
    }
    return (otherType.type === 'TSStringKeyword' ||
        otherType.type === 'TSNumberKeyword' ||
        otherType.type === 'TSTypeReference');
}
/**
 * Detects generic type patterns where `& {}` serves a legitimate purpose:
 * 1. Mapped type pattern: `{ [K in keyof T]: T[K] } & {}` - forces type flattening (Simplify/Prettify)
 * 2. Generic type reference: `GenericType<T> & {}` where GenericType has type arguments
 * 3. Type parameter reference: `T & {}` where T is a type parameter
 *
 * These patterns are used for type normalization and non-nullability constraints.
 */
function isGenericTypePattern(intersection, emptyTypeNode, parserServices) {
    const siblingTypes = intersection.types.filter(t => t !== emptyTypeNode);
    return siblingTypes.some(siblingType => {
        // Pattern 1: Mapped type (Simplify/Prettify pattern)
        if (siblingType.type === 'TSMappedType') {
            return true;
        }
        // Pattern 2: Generic type reference with type arguments
        if (siblingType.type === 'TSTypeReference' && siblingType.typeArguments) {
            return true;
        }
        // Pattern 3: Type parameter reference (e.g., T & {})
        if (siblingType.type === 'TSTypeReference') {
            const tp = parserServices.program
                .getTypeChecker()
                .getTypeAtLocation(parserServices.esTreeNodeToTSNodeMap.get(siblingType));
            if (tp.isTypeParameter()) {
                return true;
            }
        }
        return false;
    });
}
