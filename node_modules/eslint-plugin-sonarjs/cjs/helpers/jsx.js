"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.getJsxShortCircuitNodes = getJsxShortCircuitNodes;
function getJsxShortCircuitNodes(logicalExpression) {
    if (logicalExpression.parent?.type === 'JSXExpressionContainer') {
        return flattenJsxShortCircuitNodes(logicalExpression, logicalExpression);
    }
    else {
        return null;
    }
}
function flattenJsxShortCircuitNodes(root, node) {
    if (node.type === 'ConditionalExpression' ||
        (node.type === 'LogicalExpression' && node.operator !== root.operator)) {
        return null;
    }
    else if (node.type === 'LogicalExpression') {
        const leftNodes = flattenJsxShortCircuitNodes(root, node.left);
        const rightNodes = flattenJsxShortCircuitNodes(root, node.right);
        if (leftNodes == null || rightNodes == null) {
            return null;
        }
        return [...leftNodes, node, ...rightNodes];
    }
    else {
        return [];
    }
}
