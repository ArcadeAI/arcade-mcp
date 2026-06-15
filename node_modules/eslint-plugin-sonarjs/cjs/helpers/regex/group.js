"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.extractReferences = extractReferences;
const ast_js_1 = require("../ast.js");
function extractReferences(node) {
    const references = [];
    if ((0, ast_js_1.isStringLiteral)(node)) {
        const str = node.value;
        const reg = /\$(\d+)|\$<([a-zA-Z]\w*)>/g;
        let match;
        while ((match = reg.exec(str)) !== null) {
            const [raw, index, name] = match;
            const value = index || name;
            references.push({ raw, value });
        }
    }
    return references;
}
