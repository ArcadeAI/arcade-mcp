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
// https://sonarsource.github.io/rspec/#/rspec/S4782/javascript
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
const parser_services_js_1 = require("../helpers/parser-services.js");
const location_js_1 = require("../helpers/location.js");
const meta = __importStar(require("./generated-meta.js"));
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, { hasSuggestions: true }),
    create(context) {
        if (!(0, parser_services_js_1.isRequiredParserServices)(context.sourceCode.parserServices)) {
            return {};
        }
        const compilerOptions = context.sourceCode.parserServices.program.getCompilerOptions();
        if (compilerOptions.exactOptionalPropertyTypes) {
            return {};
        }
        function checkProperty(node) {
            const tsNode = node;
            const optionalToken = context.sourceCode.getFirstToken(node, token => token.value === '?');
            if (!tsNode.optional || !optionalToken) {
                return;
            }
            const typeNode = getUndefinedTypeAnnotation(tsNode.typeAnnotation);
            if (typeNode) {
                const suggest = getQuickFixSuggestions(context, optionalToken, typeNode);
                (0, location_js_1.report)(context, {
                    message: "Consider removing 'undefined' type or '?' specifier, one of them is redundant.",
                    loc: optionalToken.loc,
                    suggest,
                }, [(0, location_js_1.toSecondaryLocation)(typeNode)]);
            }
        }
        return {
            'PropertyDefinition, TSPropertySignature': (node) => checkProperty(node),
        };
    },
};
function getUndefinedTypeAnnotation(tsTypeAnnotation) {
    if (tsTypeAnnotation) {
        return getUndefinedTypeNode(tsTypeAnnotation.typeAnnotation);
    }
    return undefined;
}
function getUndefinedTypeNode(typeNode) {
    if (typeNode.type === 'TSUndefinedKeyword') {
        return typeNode;
    }
    else if (typeNode.type === 'TSUnionType') {
        return typeNode.types.map(getUndefinedTypeNode).find(tpe => tpe !== undefined);
    }
    return undefined;
}
function getQuickFixSuggestions(context, optionalToken, undefinedType) {
    const suggestions = [
        {
            desc: 'Remove "?" operator',
            fix: fixer => fixer.remove(optionalToken),
        },
    ];
    if (undefinedType.parent?.type === 'TSUnionType') {
        suggestions.push(getUndefinedRemovalSuggestion(context, undefinedType));
    }
    return suggestions;
}
function getUndefinedRemovalSuggestion(context, undefinedType) {
    return {
        desc: 'Remove "undefined" type annotation',
        fix: fixer => {
            const fixes = [];
            const unionType = undefinedType.parent;
            if (unionType.types.length === 2) {
                const unionTypeNode = unionType;
                const otherType = unionType.types[0] === undefinedType ? unionType.types[1] : unionType.types[0];
                const otherTypeText = context.sourceCode.getText(otherType);
                fixes.push(fixer.replaceText(unionTypeNode, otherTypeText));
                const tokenBefore = context.sourceCode.getTokenBefore(unionTypeNode);
                const tokenAfter = context.sourceCode.getTokenAfter(unionTypeNode);
                if (tokenBefore?.value === '(' && tokenAfter?.value === ')') {
                    fixes.push(fixer.remove(tokenBefore), fixer.remove(tokenAfter));
                }
            }
            else {
                const index = unionType.types.indexOf(undefinedType);
                if (index === 0) {
                    fixes.push(fixer.removeRange([undefinedType.range[0], unionType.types[1].range[0]]));
                }
                else {
                    fixes.push(fixer.removeRange([unionType.types[index - 1].range[1], undefinedType.range[1]]));
                }
            }
            return fixes;
        },
    };
}
