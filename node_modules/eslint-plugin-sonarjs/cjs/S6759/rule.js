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
// https://sonarsource.github.io/rspec/#/rspec/S6759/javascript
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
const type_js_1 = require("../helpers/type.js");
const ast_js_1 = require("../helpers/ast.js");
const collection_js_1 = require("../helpers/collection.js");
const ts_api_utils_1 = require("ts-api-utils");
const typescript_1 = __importDefault(require("typescript"));
const meta = __importStar(require("./generated-meta.js"));
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        hasSuggestions: true,
        messages: {
            readOnlyProps: 'Mark the props of the component as read-only.',
            readOnlyPropsFix: 'Mark the props as read-only',
        },
    }),
    create(context) {
        const services = context.sourceCode.parserServices;
        if (!(0, parser_services_js_1.isRequiredParserServices)(services)) {
            return {};
        }
        const functionInfo = [];
        return {
            ':function'() {
                functionInfo.push({ returns: [] });
            },
            ':function:exit'(node) {
                /* Functional component */
                const info = functionInfo.pop();
                if (!info || !isFunctionalComponent(node, info)) {
                    return;
                }
                /* Provides props */
                const [props] = node.params;
                if (!props) {
                    return;
                }
                /* Includes type annotation */
                const { typeAnnotation } = props;
                if (!typeAnnotation) {
                    return;
                }
                /* Read-only props */
                if (!isReadOnly(props, services)) {
                    context.report({
                        node: props,
                        messageId: 'readOnlyProps',
                        suggest: [
                            {
                                messageId: 'readOnlyPropsFix',
                                fix(fixer) {
                                    const tpe = typeAnnotation.typeAnnotation;
                                    const oldText = context.sourceCode.getText(tpe);
                                    const newText = `Readonly<${oldText}>`;
                                    return fixer.replaceText(tpe, newText);
                                },
                            },
                        ],
                    });
                }
            },
            ReturnStatement(node) {
                const current = (0, collection_js_1.last)(functionInfo);
                if (current) {
                    current.returns.push(node);
                }
            },
        };
        /**
         * A function is considered to be a React functional component if it
         * is a named function declaration with a starting uppercase letter,
         * it takes at most one parameter, and it returns some JSX value.
         */
        function isFunctionalComponent(node, info) {
            /* Named function declaration */
            if (node.type !== 'FunctionDeclaration' || node.id === null) {
                return false;
            }
            /* Starts with uppercase */
            const name = node.id.name;
            if (!(name && /^[A-Z]/.test(name))) {
                return false;
            }
            /* At most one parameter (for props) */
            const paramCount = node.params.length;
            if (paramCount > 1) {
                return false;
            }
            /* Returns JSX value */
            const { returns } = info;
            for (const ret of returns) {
                if (!ret.argument) {
                    continue;
                }
                const value = (0, ast_js_1.getUniqueWriteUsageOrNode)(context, ret.argument);
                if (value.type.startsWith('JSX')) {
                    return true;
                }
            }
            return false;
        }
    },
};
/**
 * A props type is considered to be read-only if the type annotation
 * is decorated with TypeScript utility type `Readonly` or if all its
 * resolved properties are read-only (regardless of how the type was constructed).
 */
function isReadOnly(props, services) {
    const type = (0, type_js_1.getTypeFromTreeNode)(props, services);
    const checker = services.program.getTypeChecker();
    /* Readonly utility type */
    if (type.aliasSymbol?.escapedName === 'Readonly') {
        return true;
    }
    /* Non-object types (primitives) don't need readonly marking */
    if (!(type.flags & typescript_1.default.TypeFlags.Object)) {
        return true;
    }
    /* Check all properties of the resolved type */
    const properties = type.getProperties();
    if (properties.length === 0) {
        /* No properties - consider read-only to avoid noise */
        return true;
    }
    /* All properties must be read-only */
    return properties.every(property => (0, ts_api_utils_1.isPropertyReadonlyInType)(type, property.getEscapedName(), checker));
}
