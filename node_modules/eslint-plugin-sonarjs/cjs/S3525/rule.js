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
// https://sonarsource.github.io/rspec/#/rspec/S3525/javascript
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
const meta = __importStar(require("./generated-meta.js"));
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            declareClass: 'Declare a "{{class}}" class and move this declaration of "{{declaration}}" into it.',
        },
    }),
    create(context) {
        const services = context.sourceCode.parserServices;
        const isFunction = (0, parser_services_js_1.isRequiredParserServices)(services) ? isFunctionType : isFunctionLike;
        return {
            AssignmentExpression: (node) => {
                const { left, right } = node;
                if (left.type === 'MemberExpression' && isFunction(right, services)) {
                    const [member, prototype] = [left.object, left.property];
                    if (member.type === 'MemberExpression' && prototype.type === 'Identifier') {
                        const [klass, property] = [member.object, member.property];
                        if (klass.type === 'Identifier' &&
                            property.type === 'Identifier' &&
                            property.name === 'prototype') {
                            context.report({
                                messageId: 'declareClass',
                                data: {
                                    class: klass.name,
                                    declaration: prototype.name,
                                },
                                node: left,
                            });
                        }
                    }
                }
            },
        };
    },
};
function isFunctionType(node, services) {
    const type = (0, type_js_1.getTypeFromTreeNode)(node, services);
    return type.symbol && (type.symbol.flags & typescript_1.default.SymbolFlags.Function) !== 0;
}
function isFunctionLike(node, _services) {
    return ['FunctionDeclaration', 'FunctionExpression', 'ArrowFunctionExpression'].includes(node.type);
}
