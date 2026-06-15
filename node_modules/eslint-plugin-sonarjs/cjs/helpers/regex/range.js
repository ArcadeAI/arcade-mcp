"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.getRegexpRange = getRegexpRange;
const collection_js_1 = require("../collection.js");
const ast_js_1 = require("../ast.js");
const tokenizer_js_1 = require("./tokenizer.js");
/**
 * Returns the location of regexpNode relative to the node, which is regexp string or literal. If the computation
 * of location fails, it returns the range of the whole node.
 */
function getRegexpRange(node, regexpNode) {
    if ((0, ast_js_1.isRegexLiteral)(node)) {
        return [regexpNode.start, regexpNode.end];
    }
    if ((0, ast_js_1.isStringLiteral)(node)) {
        if (node.value === '') {
            return [0, 2];
        }
        const s = node.raw;
        const tokens = (0, tokenizer_js_1.tokenizeString)(unquote(s));
        if (regexpNode.start === regexpNode.end) {
            // this happens in case of empty alternative node like '|'
            if (regexpNode.start - 1 < tokens.length) {
                // '|' first empty alternative will have start = 1, end = 1
                // +1 is to account for string quote
                return [
                    tokens[regexpNode.start - 1].range[0] + 1,
                    tokens[regexpNode.start - 1].range[0] + 1,
                ];
            }
            else {
                // '|' second empty alternative regex node will have start = 2, end = 2
                // +1 is to account for string quote
                return [(0, collection_js_1.last)(tokens).range[1] + 1, (0, collection_js_1.last)(tokens).range[1] + 1];
            }
        }
        // regexpNode positions are 1 - based, we need to -1 to report as 0 - based
        // it's possible for node start to be outside of range, e.g. `a` in new RegExp('//a')
        const startToken = regexpNode.start - 1;
        if (tokens[startToken] === undefined) {
            // fallback when something is broken
            return nodeRange(node);
        }
        const start = tokens[startToken].range[0];
        // it's possible for node end to be outside of range, e.g. new RegExp('\n(|)')
        const endToken = Math.min(regexpNode.end - 2, tokens.length - 1);
        if (tokens[endToken] === undefined) {
            // fallback when something is broken
            return nodeRange(node);
        }
        const end = tokens[endToken].range[1];
        // +1 is needed to account for string quotes
        return [start + 1, end + 1];
    }
    if (node.type === 'TemplateLiteral') {
        // we don't support these properly
        return nodeRange(node);
    }
    throw new Error(`Expected regexp or string literal, got ${node.type}`);
}
function nodeRange(node) {
    return [0, node.range[1] - node.range[0]];
}
function unquote(s) {
    if (!s.startsWith("'") && !s.startsWith('"')) {
        throw new Error(`invalid string to unquote: ${s}`);
    }
    return s.substring(1, s.length - 1);
}
