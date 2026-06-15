"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.findFirstMatchingLocalAncestor = findFirstMatchingLocalAncestor;
exports.findFirstMatchingAncestor = findFirstMatchingAncestor;
exports.localAncestorsChain = localAncestorsChain;
exports.ancestorsChain = ancestorsChain;
exports.getParent = getParent;
exports.getNodeParent = getNodeParent;
exports.childrenOf = childrenOf;
exports.isTsAncestor = isTsAncestor;
const ast_js_1 = require("./ast.js");
function findFirstMatchingLocalAncestor(node, predicate) {
    return localAncestorsChain(node).find(predicate);
}
function findFirstMatchingAncestor(node, predicate) {
    return ancestorsChain(node, new Set()).find(predicate);
}
function localAncestorsChain(node) {
    return ancestorsChain(node, ast_js_1.functionLike);
}
function ancestorsChain(node, boundaryTypes) {
    const chain = [];
    let currentNode = node.parent;
    while (currentNode) {
        chain.push(currentNode);
        if (boundaryTypes.has(currentNode.type)) {
            break;
        }
        currentNode = currentNode.parent;
    }
    return chain;
}
function getParent(context, node) {
    const ancestors = context.sourceCode.getAncestors(node);
    return ancestors.length > 0 ? ancestors.at(-1) : undefined;
}
/**
 * Returns the parent of an ESLint node
 *
 * This function assumes that an ESLint node exposes a parent property,
 * which is always defined. However, it's better to use `getParent` if
 * it is possible to retrieve the parent based on the rule context.
 *
 * It should eventually disappear once we come up with a proper solution
 * against the conflicting typings between ESLint and TypeScript ESLint
 * when it comes to the parent of a node.
 *
 * @param node an ESLint node
 * @returns the parent node
 */
function getNodeParent(node) {
    return node.parent;
}
/**
 * Returns the direct children of a node
 * @param node the node to get the children
 * @param visitorKeys the visitor keys provided by the source code
 * @returns the node children
 */
function childrenOf(node, visitorKeys) {
    const keys = visitorKeys[node.type];
    const children = [];
    if (keys) {
        for (const key of keys) {
            /**
             * A node's child may be a node or an array of nodes, e.g., `body` in `estree.Program`.
             * If it's an array, we extract all the nodes from it; if not, we just add the node.
             */
            const child = node[key];
            if (Array.isArray(child)) {
                children.push(...child);
            }
            else {
                children.push(child);
            }
        }
    }
    return children.filter(Boolean);
}
function isTsAncestor(candidate, node) {
    let current = node.parent;
    while (current) {
        if (current === candidate) {
            return true;
        }
        current = current.parent;
    }
    return false;
}
