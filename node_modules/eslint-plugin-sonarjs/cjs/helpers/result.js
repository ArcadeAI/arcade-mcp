"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.Result = void 0;
exports.getResultOfExpression = getResultOfExpression;
const ast_js_1 = require("./ast.js");
class Result {
    constructor(ctx, node, status) {
        this.ctx = ctx;
        this.node = node;
        this.status = status;
    }
    get isFound() {
        return this.status === 'found';
    }
    get isMissing() {
        return this.status === 'missing';
    }
    get isTrue() {
        return this.isFound && (0, ast_js_1.isBooleanLiteral)(this.node) && this.node.value;
    }
    ofType(type) {
        return this.isFound && this.node.type === type;
    }
    getArgument(position) {
        if (!this.isFound) {
            return this;
        }
        else if (this.node.type !== 'NewExpression' && this.node.type !== 'CallExpression') {
            return unknown(this.ctx, this.node);
        }
        const argument = this.node.arguments[position];
        if (argument == null) {
            return missing(this.ctx, this.node);
        }
        else {
            return getResultOfExpression(this.ctx, argument);
        }
    }
    getProperty(propertyName) {
        if (!this.isFound) {
            return this;
        }
        else if (this.node.type !== 'ObjectExpression') {
            return unknown(this.ctx, this.node);
        }
        const property = (0, ast_js_1.getProperty)(this.node, propertyName, this.ctx);
        if (property === undefined) {
            return unknown(this.ctx, this.node);
        }
        else if (property === null) {
            return missing(this.ctx, this.node);
        }
        else {
            return getResultOfExpression(this.ctx, property.value);
        }
    }
    getMemberObject() {
        if (!this.isFound) {
            return this;
        }
        else if (this.node.type === 'MemberExpression') {
            return getResultOfExpression(this.ctx, this.node.object).filter(n => n.type !== 'Super');
        }
        else {
            return unknown(this.ctx, this.node);
        }
    }
    findInArray(closure) {
        if (!this.isFound) {
            return this;
        }
        else if (!(0, ast_js_1.isArrayExpression)(this.node)) {
            return unknown(this.ctx, this.node);
        }
        let isMissing = true;
        for (const element of this.node.elements) {
            const result = element == null ? null : closure(getResultOfExpression(this.ctx, element));
            if (result?.isFound) {
                return result;
            }
            isMissing &&= result?.isMissing ?? true;
        }
        return isMissing ? missing(this.ctx, this.node) : unknown(this.ctx, this.node);
    }
    everyStringLiteral(closure) {
        if (!this.isFound) {
            return false;
        }
        else if ((0, ast_js_1.isStringLiteral)(this.node)) {
            return closure(this.node);
        }
        else if (!(0, ast_js_1.isArrayExpression)(this.node)) {
            return false;
        }
        for (const element of this.node.elements) {
            const child = element == null ? null : getResultOfExpression(this.ctx, element);
            if (!child?.isFound || !(0, ast_js_1.isStringLiteral)(child.node) || !closure(child.node)) {
                return false;
            }
        }
        return true;
    }
    asStringLiterals() {
        if (!this.isFound) {
            return [];
        }
        const values = [];
        if ((0, ast_js_1.isArrayExpression)(this.node)) {
            for (const arg of this.node.elements) {
                const result = arg == null ? null : getResultOfExpression(this.ctx, arg);
                if (result?.isFound && (0, ast_js_1.isStringLiteral)(result.node)) {
                    values.push(result.node);
                }
            }
        }
        else if ((0, ast_js_1.isStringLiteral)(this.node)) {
            values.push(this.node);
        }
        return values;
    }
    map(closure) {
        return this.isFound ? closure(this.node) : null;
    }
    filter(closure) {
        if (!this.isFound) {
            return this;
        }
        return closure(this.node, this.ctx) ? this : unknown(this.ctx, this.node);
    }
}
exports.Result = Result;
function unknown(ctx, node) {
    return new Result(ctx, node, 'unknown');
}
function missing(ctx, node) {
    return new Result(ctx, node, 'missing');
}
function found(ctx, node) {
    return new Result(ctx, node, 'found');
}
function getResultOfExpression(ctx, node) {
    const value = (0, ast_js_1.getUniqueWriteUsageOrNode)(ctx, node, true);
    return (0, ast_js_1.isUndefined)(value) ? missing(ctx, value) : found(ctx, value);
}
