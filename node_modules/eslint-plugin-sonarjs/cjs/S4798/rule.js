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
// https://sonarsource.github.io/rspec/#/rspec/S4798/javascript
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
const meta = __importStar(require("./generated-meta.js"));
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            provideDefault: "Provide a default value for '{{parameter}}' so that " +
                'the logic of the function is more evident when this parameter is missing. ' +
                'Consider defining another function if providing default value is not possible.',
        },
    }),
    create(context) {
        return {
            'FunctionDeclaration, FunctionExpression, ArrowFunctionExpression': (node) => {
                const functionLike = node;
                for (const param of functionLike.params) {
                    if (param.type === 'Identifier' && isOptionalBoolean(param)) {
                        context.report({
                            messageId: 'provideDefault',
                            data: {
                                parameter: param.name,
                            },
                            node: param,
                        });
                    }
                }
            },
        };
    },
};
function isOptionalBoolean(node) {
    return usesQuestionOptionalSyntax(node) || usesUnionUndefinedOptionalSyntax(node);
}
/**
 * Matches "param?: boolean"
 */
function usesQuestionOptionalSyntax(node) {
    return (!!node.optional &&
        !!node.typeAnnotation &&
        node.typeAnnotation.typeAnnotation.type === 'TSBooleanKeyword');
}
/**
 * Matches "boolean | undefined"
 */
function usesUnionUndefinedOptionalSyntax(node) {
    if (!!node.typeAnnotation && node.typeAnnotation.typeAnnotation.type === 'TSUnionType') {
        const types = node.typeAnnotation.typeAnnotation.types;
        return (types.length === 2 &&
            types.some(tp => tp.type === 'TSBooleanKeyword') &&
            types.some(tp => tp.type === 'TSUndefinedKeyword'));
    }
    return false;
}
