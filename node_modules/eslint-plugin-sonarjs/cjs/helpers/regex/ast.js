"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.isRegExpConstructor = isRegExpConstructor;
exports.isStringReplaceCall = isStringReplaceCall;
exports.isStringRegexMethodCall = isStringRegexMethodCall;
const ast_js_1 = require("../ast.js");
const type_js_1 = require("../type.js");
function isRegExpConstructor(node) {
    return (((node.type === 'CallExpression' || node.type === 'NewExpression') &&
        node.callee.type === 'Identifier' &&
        node.callee.name === 'RegExp' &&
        node.arguments.length > 0) ||
        isRegExpWithGlobalThis(node));
}
function isStringReplaceCall(call, services) {
    return (call.callee.type === 'MemberExpression' &&
        call.callee.property.type === 'Identifier' &&
        !call.callee.computed &&
        ['replace', 'replaceAll'].includes(call.callee.property.name) &&
        call.arguments.length > 1 &&
        (0, type_js_1.isString)(call.callee.object, services));
}
function isStringRegexMethodCall(call, services) {
    return (call.callee.type === 'MemberExpression' &&
        call.callee.property.type === 'Identifier' &&
        !call.callee.computed &&
        ['match', 'matchAll', 'search'].includes(call.callee.property.name) &&
        call.arguments.length > 0 &&
        (0, type_js_1.isString)(call.callee.object, services) &&
        (0, type_js_1.isString)(call.arguments[0], services));
}
function isRegExpWithGlobalThis(node) {
    return (node.type === 'NewExpression' &&
        node.callee.type === 'MemberExpression' &&
        (0, ast_js_1.isIdentifier)(node.callee.object, 'globalThis') &&
        (0, ast_js_1.isIdentifier)(node.callee.property, 'RegExp') &&
        node.arguments.length > 0);
}
