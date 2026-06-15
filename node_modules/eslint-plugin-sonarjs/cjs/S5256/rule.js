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
// https://sonarsource.github.io/rspec/#/rspec/S5256/javascript
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
const jsx_ast_utils_x_1 = __importDefault(require("jsx-ast-utils-x"));
const { getLiteralPropValue, getProp } = jsx_ast_utils_x_1.default;
const table_js_1 = require("../helpers/table.js");
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const accessibility_js_1 = require("../helpers/accessibility.js");
const meta = __importStar(require("./generated-meta.js"));
/**
 * Detects reusable table wrapper components that receive children via props spread.
 * Returns true if the table has no JSX children AND has a JSXSpreadAttribute.
 */
function isReusableWrapperComponent(tree) {
    const hasNoChildren = tree.children.length === 0;
    const hasSpreadAttribute = tree.openingElement.attributes.some(attr => attr.type === 'JSXSpreadAttribute');
    return hasNoChildren && hasSpreadAttribute;
}
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta),
    create(context) {
        const checkValidTable = (tree) => {
            const grid = (0, table_js_1.computeGrid)(context, tree);
            if (grid === null) {
                // Unknown table structure, dont raise issue
                return true;
            }
            if (grid.length === 0) {
                return false;
            }
            for (const row of grid) {
                if (row.every(({ isHeader }) => isHeader)) {
                    return true;
                }
            }
            for (let col = 0; col < grid[0].length; col++) {
                if (grid.every(row => col >= row.length || row[col].isHeader)) {
                    return true;
                }
            }
            return false;
        };
        return {
            JSXElement(node) {
                const tree = node;
                const elementType = (0, accessibility_js_1.getElementType)(context)(tree.openingElement);
                if (elementType === 'table') {
                    if ((0, accessibility_js_1.isPresentationTable)(context, tree.openingElement)) {
                        return;
                    }
                    const ariaHidden = getProp(tree.openingElement.attributes, 'aria-hidden');
                    if (ariaHidden && getLiteralPropValue(ariaHidden) === true) {
                        return;
                    }
                    // Skip reusable wrapper components: tables with no children and spread props
                    // where table structure is provided via props.children at usage sites
                    if (isReusableWrapperComponent(tree)) {
                        return;
                    }
                    if (!checkValidTable(tree)) {
                        context.report({
                            node,
                            message: 'Add a valid header row or column to this "<table>".',
                        });
                    }
                }
            },
        };
    },
};
