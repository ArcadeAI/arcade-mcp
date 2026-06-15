"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.isTestConstruct = isTestConstruct;
exports.extractTestCase = extractTestCase;
exports.isTestCase = isTestCase;
exports.isDescribeCase = isDescribeCase;
const ast_js_1 = require("./ast.js");
const TEST_CONSTRUCTS = [
    'describe',
    'context',
    'it',
    'specify',
    'before',
    'after',
    'beforeEach',
    'afterEach',
];
function isTestConstruct(node, constructs = TEST_CONSTRUCTS) {
    return constructs.some(construct => {
        return (node.type === 'CallExpression' &&
            ((0, ast_js_1.isIdentifier)(node.callee, construct) ||
                (node.callee.type === 'MemberExpression' &&
                    (0, ast_js_1.isIdentifier)(node.callee.object, construct) &&
                    (0, ast_js_1.isIdentifier)(node.callee.property, 'only', 'skip'))));
    });
}
function extractTestCase(node) {
    if (isTestCase(node)) {
        const callExpr = node;
        const [, callback] = callExpr.arguments;
        if (callback && ast_js_1.FUNCTION_NODES.includes(callback.type)) {
            return { node: callExpr.callee, callback: callback };
        }
    }
    return null;
}
/**
 * returns true if the node is a test case
 *
 * @param node
 * @returns
 */
function isTestCase(node) {
    return isTestConstruct(node, ['it', 'specify']);
}
/**
 * returns true if the node is a describe block
 *
 * @param node
 * @returns
 */
function isDescribeCase(node) {
    return isTestConstruct(node, ['describe']);
}
