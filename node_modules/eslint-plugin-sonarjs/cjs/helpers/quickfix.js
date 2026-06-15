"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.removeNodeWithLeadingWhitespaces = removeNodeWithLeadingWhitespaces;
const collection_js_1 = require("./collection.js");
function removeNodeWithLeadingWhitespaces(context, node, fixer, removeUntil) {
    const previousComments = context.sourceCode.getCommentsBefore(node);
    let start = 0;
    if (previousComments.length === 0) {
        const previousToken = context.sourceCode.getTokenBefore(node);
        if (previousToken) {
            start = previousToken.range[1];
        }
    }
    else {
        start = (0, collection_js_1.last)(previousComments).range[1];
    }
    const end = removeUntil ?? node.range[1];
    return fixer.removeRange([start, end]);
}
