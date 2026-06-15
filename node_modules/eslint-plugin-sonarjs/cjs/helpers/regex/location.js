"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.getRegexpLocation = getRegexpLocation;
const ast_js_1 = require("../ast.js");
const range_js_1 = require("./range.js");
/**
 * Gets the regexp node location in the ESLint referential
 * @param node the ESLint regex node
 * @param regexpNode the regexp regex node
 * @param context the rule context
 * @param offset an offset to apply on the location
 * @returns the regexp node location in the ESLint referential
 */
function getRegexpLocation(node, regexpNode, context, offset = [0, 0]) {
    let loc;
    if ((0, ast_js_1.isRegexLiteral)(node) || (0, ast_js_1.isStringLiteral)(node)) {
        const source = context.sourceCode;
        const [start] = node.range;
        const [reStart, reEnd] = (0, range_js_1.getRegexpRange)(node, regexpNode);
        const locationStart = start + reStart + offset[0];
        const locationEnd = start + reEnd + offset[1];
        if (locationStart === locationEnd) {
            return null;
        }
        else {
            loc = {
                start: source.getLocFromIndex(locationStart),
                end: source.getLocFromIndex(locationEnd),
            };
        }
    }
    else {
        loc = node.loc;
    }
    return loc;
}
