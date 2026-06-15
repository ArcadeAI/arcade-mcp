"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.computeGrid = computeGrid;
const jsx_ast_utils_x_1 = __importDefault(require("jsx-ast-utils-x"));
const { getLiteralPropValue, getProp } = jsx_ast_utils_x_1.default;
const isHtmlElement_js_1 = require("./isHtmlElement.js");
const accessibility_js_1 = require("./accessibility.js");
const MAX_ROW_SPAN = 65534;
const MAX_COL_SPAN = 1000;
const KNOWN_TABLE_STRUCTURE_ELEMENTS = new Set(['thead', 'tbody', 'tfoot']);
function computeSpan(tree, spanKey) {
    let span = 1;
    const spanAttr = getProp(tree.openingElement.attributes, spanKey);
    if (spanAttr) {
        span = Number.parseInt(String(getLiteralPropValue(spanAttr)));
    }
    return span;
}
function rowSpan(tree) {
    let value = computeSpan(tree, 'rowspan');
    // Special case: 0 is valid for rowspan (means span all remaining rows)
    if (value === 0) {
        return 0;
    }
    if (value < 1) {
        value = 1;
    }
    if (value > MAX_ROW_SPAN) {
        value = MAX_ROW_SPAN;
    }
    return value;
}
function colSpan(tree) {
    let value = computeSpan(tree, 'colspan');
    if (value < 1) {
        value = 1;
    }
    else if (value > MAX_COL_SPAN) {
        value = MAX_COL_SPAN;
    }
    return value;
}
function getHeaders(tree) {
    const headers = getProp(tree.openingElement.attributes, 'headers');
    if (headers) {
        const headerVal = getLiteralPropValue(headers);
        if (headerVal && String(headerVal).trim() !== '') {
            return String(headerVal).split(/\s+/);
        }
    }
    return undefined;
}
function getID(tree) {
    const id = getProp(tree.openingElement.attributes, 'id');
    if (id) {
        return String(getLiteralPropValue(id));
    }
    return undefined;
}
function createTableCell(internalCell) {
    // Drop rowSpan from the cell
    const { rowSpan, ...tableCell } = internalCell;
    return tableCell;
}
function extractRows(context, tree) {
    const rows = [];
    let internalNodeCount = 0;
    let unknownTableStructure = false;
    const extractRow = (tree) => {
        const row = [];
        for (const child of tree.children) {
            if ((child.type === 'JSXExpressionContainer' &&
                child.expression.type === 'JSXEmptyExpression') ||
                child.type === 'JSXText') {
                // Skip comment
                continue;
            }
            const isTdOrTh = child.type === 'JSXElement' &&
                child.openingElement.name.type === 'JSXIdentifier' &&
                ['td', 'th'].includes(child.openingElement.name.name);
            if (!isTdOrTh) {
                return null;
            }
            const colSpanValue = colSpan(child);
            const rowSpanValue = rowSpan(child);
            if (Number.isNaN(colSpanValue) || Number.isNaN(rowSpanValue)) {
                return null;
            }
            const headers = getHeaders(child);
            const id = getID(child);
            for (let i = 0; i < colSpanValue; i++) {
                row.push({
                    rowSpan: rowSpanValue,
                    isHeader: child.openingElement.name.type === 'JSXIdentifier' &&
                        child.openingElement.name.name === 'th',
                    headers,
                    id,
                    node: child,
                    internalNodeId: internalNodeCount,
                });
            }
            internalNodeCount += 1;
        }
        return row;
    };
    const handleInternalStructure = (tree) => {
        const extractedRows = extractRows(context, tree);
        if (extractedRows === null) {
            unknownTableStructure = true;
        }
        else if (extractedRows.length > 0) {
            rows.push(...extractedRows);
        }
    };
    for (const child of tree.children) {
        if (child.type === 'JSXElement') {
            const childType = (0, accessibility_js_1.getElementType)(context)(child.openingElement).toLowerCase();
            if (childType === 'tr') {
                const extractedRow = extractRow(child);
                if (extractedRow) {
                    rows.push(extractedRow);
                }
                else {
                    unknownTableStructure = true;
                }
            }
            else if (childType === 'table') {
                // skip
            }
            else if (KNOWN_TABLE_STRUCTURE_ELEMENTS.has(childType)) {
                handleInternalStructure(child);
            }
            else if (!(0, isHtmlElement_js_1.isHtmlElement)(child)) {
                unknownTableStructure = true;
            }
        }
        else if (child.type === 'JSXExpressionContainer' &&
            child.expression.type !== 'JSXEmptyExpression') {
            unknownTableStructure = true;
        }
        else if (child.type === 'JSXFragment') {
            handleInternalStructure(child);
        }
    }
    if (unknownTableStructure) {
        return null;
    }
    return rows;
}
function computeGrid(context, tree) {
    const rows = extractRows(context, tree);
    if (rows === null) {
        return null;
    }
    if (rows.length === 0) {
        return [];
    }
    const nbColumns = rows[0].length;
    const columns = Array.from({ length: nbColumns });
    let row = 0;
    const result = [];
    while (row < rows.length) {
        const resultRow = [];
        let indexInRow = 0;
        // Checks if any of the cells in the current row that is added was used from the incoming rows[row]
        let usedCurrentRow = false;
        // Checks if row was built entirely out of columns with rowSpan == 0
        let onlyMaxRowSpan = true;
        for (let column = 0; column < nbColumns; column++) {
            if (!columns[column]) {
                if (indexInRow === rows[row].length) {
                    // We have reached the end of the current row from the table definition
                    continue;
                }
                columns[column] = rows[row][indexInRow];
                indexInRow++;
                usedCurrentRow = true;
            }
            const currentCell = columns[column];
            if (!currentCell) {
                continue;
            }
            resultRow.push(createTableCell(currentCell));
            if (currentCell.rowSpan > 0) {
                // Mark that there is at least one cell that is not built entirely out of columns with rowSpan == 0
                onlyMaxRowSpan = false;
                currentCell.rowSpan--;
                if (currentCell.rowSpan === 0) {
                    columns[column] = undefined;
                }
            }
        }
        if (onlyMaxRowSpan) {
            // If the row was built entirely out of columns with rowSpan == 0, we finish the construction
            break;
        }
        result.push(resultRow);
        if (usedCurrentRow) {
            // Increment the row index only if we used any of the cells from the incoming rows[row]
            row++;
        }
    }
    return result;
}
