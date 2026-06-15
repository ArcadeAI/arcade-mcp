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
// https://sonarsource.github.io/rspec/#/rspec/S3402/javascript
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
const parser_services_js_1 = require("../helpers/parser-services.js");
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const type_js_1 = require("../helpers/type.js");
const ast_js_1 = require("../helpers/ast.js");
const location_js_1 = require("../helpers/location.js");
const meta = __importStar(require("./generated-meta.js"));
const message = `Review this expression to be sure that the concatenation was intended.`;
const objectLikeTypes = new Set(['object', 'Object']);
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta),
    create(context) {
        const services = context.sourceCode.parserServices;
        if (!(0, parser_services_js_1.isRequiredParserServices)(services)) {
            return {};
        }
        const checker = services.program.getTypeChecker();
        function isStringPlusNonString(type1, type2) {
            if (isLiteralType(type1) || isLiteralType(type2)) {
                return false;
            }
            const isObjectLike = objectLikeTypes.has(checker.typeToString(type2));
            // @ts-ignore private API, see https://github.com/microsoft/TypeScript/issues/9879
            return isStringType(type1) && !isObjectLike && !checker.isTypeAssignableTo(type1, type2);
        }
        function getOperatorLocation(left, right) {
            return context.sourceCode
                .getTokensBetween(left, right)
                .find(token => token.value === '+' || token.value === '+=').loc;
        }
        function checkConcatenation(left, right) {
            if ((0, ast_js_1.isStringLiteral)(left) ||
                (0, ast_js_1.isStringLiteral)(right) ||
                isConcatenation(left) ||
                isConcatenation(right)) {
                return;
            }
            const leftType = (0, type_js_1.getTypeFromTreeNode)(left, services);
            const rightType = (0, type_js_1.getTypeFromTreeNode)(right, services);
            if (isStringPlusNonString(leftType, rightType) ||
                isStringPlusNonString(rightType, leftType)) {
                (0, location_js_1.report)(context, {
                    message,
                    loc: getOperatorLocation(left, right),
                }, [
                    (0, location_js_1.toSecondaryLocation)(left, `left operand has type ${checker.typeToString(leftType)}.`),
                    (0, location_js_1.toSecondaryLocation)(right, `right operand has type ${checker.typeToString(rightType)}.`),
                ]);
            }
        }
        return {
            'AssignmentExpression[operator="+="]'(node) {
                checkConcatenation(node.left, node.right);
            },
            'BinaryExpression[operator="+"]'(node) {
                checkConcatenation(node.left, node.right);
            },
        };
    },
};
function isStringType(typ) {
    return (typ.getFlags() & typescript_1.default.TypeFlags.StringLike) !== 0;
}
function isLiteralType(type) {
    if (type.isUnion()) {
        return type.types.some(t => isLiteralType(t));
    }
    return type.isStringLiteral();
}
function isConcatenation(node) {
    return node.type === 'BinaryExpression' && node.operator === '+';
}
