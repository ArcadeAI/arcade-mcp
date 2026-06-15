"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.areEquivalent = areEquivalent;
/**
 * Equivalence is implemented by comparing node types and their tokens.
 * Classic implementation would recursively compare children,
 * but "estree" doesn't provide access to children when node type is unknown
 */
function areEquivalent(first, second, sourceCode) {
    if (Array.isArray(first) && Array.isArray(second)) {
        return (first.length === second.length &&
            first.every((firstNode, index) => areEquivalent(firstNode, second[index], sourceCode)));
    }
    else if (!Array.isArray(first) && !Array.isArray(second)) {
        return (first.type === second.type &&
            compareTokens(sourceCode.getTokens(first), sourceCode.getTokens(second)));
    }
    return false;
}
function compareTokens(firstTokens, secondTokens) {
    return (firstTokens.length === secondTokens.length &&
        firstTokens.every((firstToken, index) => firstToken.value === secondTokens[index].value));
}
