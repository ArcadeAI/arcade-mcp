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
// https://sonarsource.github.io/rspec/#/rspec/S3403/javascript
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
const type_js_1 = require("../helpers/type.js");
const parser_services_js_1 = require("../helpers/parser-services.js");
const location_js_1 = require("../helpers/location.js");
const meta = __importStar(require("./generated-meta.js"));
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, { hasSuggestions: true }),
    create(context) {
        const services = context.sourceCode.parserServices;
        if (!(0, parser_services_js_1.isRequiredParserServices)(services)) {
            return {};
        }
        function isComparableTo(lhs, rhs) {
            const checker = services.program.getTypeChecker();
            const lhsType = checker.getBaseTypeOfLiteralType((0, type_js_1.getTypeFromTreeNode)(lhs, services));
            const rhsType = checker.getBaseTypeOfLiteralType((0, type_js_1.getTypeFromTreeNode)(rhs, services));
            // If either type is indeterminate (unknown, type parameter, or indexed access),
            // we cannot know at compile time if the comparison will always fail
            if (isIndeterminateType(lhsType) || isIndeterminateType(rhsType)) {
                return true;
            }
            // @ts-ignore private API
            return (checker.isTypeAssignableTo(lhsType, rhsType) || checker.isTypeAssignableTo(rhsType, lhsType));
        }
        return {
            BinaryExpression: (node) => {
                const { left, operator, right } = node;
                if (['===', '!=='].includes(operator) && !isComparableTo(left, right)) {
                    const [actual, expected, outcome] = operator === '===' ? ['===', '==', 'false'] : ['!==', '!=', 'true'];
                    const operatorToken = context.sourceCode
                        .getTokensBetween(left, right)
                        .find(token => token.type === 'Punctuator' && token.value === operator);
                    (0, location_js_1.report)(context, {
                        message: `Remove this "${actual}" check; it will always be ${outcome}. Did you mean to use "${expected}"?`,
                        loc: operatorToken.loc,
                        suggest: [
                            {
                                desc: `Replace "${actual}" with "${expected}"`,
                                fix: fixer => fixer.replaceText(operatorToken, expected),
                            },
                        ],
                    }, [left, right].map(node => (0, location_js_1.toSecondaryLocation)(node)));
                }
            },
        };
    },
};
/**
 * Checks if a type is indeterminate (its actual value cannot be determined at compile time).
 * - Unknown: can be compared with anything
 * - TypeParameter: generics like T
 * - IndexedAccess: like T[K]
 */
function isIndeterminateType(type) {
    const indeterminateFlags = typescript_1.default.TypeFlags.Unknown | typescript_1.default.TypeFlags.TypeParameter | typescript_1.default.TypeFlags.IndexedAccess;
    return (type.flags & indeterminateFlags) !== 0;
}
