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
// https://sonarsource.github.io/rspec/#/rspec/S5264/javascript
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
const accessibility_js_1 = require("../helpers/accessibility.js");
const meta = __importStar(require("./generated-meta.js"));
const jsx_ast_utils_x_1 = __importDefault(require("jsx-ast-utils-x"));
const { getLiteralPropValue, getProp, getPropValue } = jsx_ast_utils_x_1.default;
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            addContent: 'Add an accessible content to this "<object>" tag.',
        },
    }),
    create(context) {
        const elementType = (0, accessibility_js_1.getElementType)(context);
        function hasVisibleChildren(children) {
            return children.some((child) => {
                switch (child.type) {
                    case 'JSXText':
                        return !!child.value.trim();
                    case 'JSXFragment':
                        return hasVisibleChildren(child.children);
                    case 'JSXElement':
                        return !isHiddenFromScreenReader(elementType(child.openingElement), child.openingElement.attributes);
                    case 'JSXExpressionContainer':
                        if (child.expression.type === 'Identifier') {
                            return child.expression.name !== 'undefined';
                        }
                        return child.expression.type !== 'JSXEmptyExpression';
                    default:
                        return false;
                }
            });
        }
        return {
            JSXElement(node) {
                const jsxNode = node;
                const type = elementType(jsxNode.openingElement);
                if (type.toLowerCase() !== 'object') {
                    return;
                }
                if (!hasVisibleChildren(jsxNode.children)) {
                    context.report({
                        node,
                        messageId: 'addContent',
                    });
                }
            },
        };
    },
};
const isHiddenFromScreenReader = (type, attributes) => {
    if (type.toUpperCase() === 'INPUT') {
        const prop = getProp(attributes, 'type');
        if (prop) {
            const hidden = getLiteralPropValue(prop);
            if (typeof hidden === 'string' && hidden.toUpperCase?.() === 'HIDDEN') {
                return true;
            }
        }
    }
    const prop = getProp(attributes, 'aria-hidden');
    return prop && getPropValue(prop) === true;
};
