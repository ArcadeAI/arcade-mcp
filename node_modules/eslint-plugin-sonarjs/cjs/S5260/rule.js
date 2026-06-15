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
// https://sonarsource.github.io/rspec/#/rspec/S5260/javascript
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
const table_js_1 = require("../helpers/table.js");
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const accessibility_js_1 = require("../helpers/accessibility.js");
const meta = __importStar(require("./generated-meta.js"));
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta),
    create(context) {
        const verifyHeaderReferences = (tree) => {
            const grid = (0, table_js_1.computeGrid)(context, tree);
            if (grid === null || grid.length === 0) {
                // Unknown table structures as well as empty tables should be considered valid
                return;
            }
            const rowHeaders = Array.from({ length: grid.length }, (_, idx) => {
                const ids = grid[idx]
                    .filter(({ isHeader, id }) => isHeader && id)
                    .map(({ id }) => id);
                return new Set(ids);
            });
            const colHeaders = Array.from({ length: grid[0].length }, (_, idx) => {
                const ids = grid
                    .map(row => row[idx])
                    .filter(Boolean)
                    .filter(({ isHeader, id }) => isHeader && id)
                    .map(({ id }) => id);
                return new Set(ids);
            });
            const allHeaders = new Set([
                ...rowHeaders.reduce((headers, acc) => new Set([...headers, ...acc]), new Set()),
                ...colHeaders.reduce((headers, acc) => new Set([...headers, ...acc]), new Set()),
            ]);
            const internalNodeToPositions = compileBlockInfo(grid);
            for (const { minRow, maxRow, minCol, maxCol, cell } of internalNodeToPositions.values()) {
                if (!cell.headers || cell.headers.length === 0) {
                    continue;
                }
                const actualHeaders = [
                    ...colHeaders.slice(minCol, maxCol + 1),
                    ...rowHeaders.slice(minRow, maxRow + 1),
                ].reduce((headers, acc) => new Set([...headers, ...acc]), new Set());
                for (const header of cell.headers) {
                    if (!actualHeaders.has(header)) {
                        if (allHeaders.has(header)) {
                            context.report({
                                node: cell.node,
                                message: `id "${header}" in "headers" references the header of another column/row.`,
                            });
                        }
                        else {
                            context.report({
                                node: cell.node,
                                message: `id "${header}" in "headers" does not reference any <th> header.`,
                            });
                        }
                    }
                }
            }
        };
        return {
            JSXElement(node) {
                const tree = node;
                const elementType = (0, accessibility_js_1.getElementType)(context)(tree.openingElement);
                if (elementType === 'table') {
                    verifyHeaderReferences(tree);
                }
            },
        };
    },
};
/**
 * Extracts an alternative representation of the blocks making up the table. Takes into account that a single block can
 * span more than just a 1x1 cell thanks to the "rowspan" and "colspan" attributes. Each block is assigned an internal
 * number during computation. Afterward, for each block, we compute its position in the resulting table.
 */
function compileBlockInfo(grid) {
    const internalNodeToPositions = new Map();
    for (const [row, element] of grid.entries()) {
        for (const [col, cell] of element.entries()) {
            if (!cell.headers) {
                continue;
            }
            const oldValue = internalNodeToPositions.get(cell.internalNodeId);
            if (oldValue === undefined) {
                internalNodeToPositions.set(cell.internalNodeId, {
                    minRow: row,
                    maxRow: row,
                    minCol: col,
                    maxCol: col,
                    cell,
                });
            }
            else {
                internalNodeToPositions.set(cell.internalNodeId, {
                    ...oldValue,
                    maxRow: row,
                    maxCol: col,
                });
            }
        }
    }
    return internalNodeToPositions;
}
