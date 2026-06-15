import type { Node } from 'estree';
import { type StringLiteral } from './ast.js';
import type { Rule } from 'eslint';
export declare class Result {
    readonly ctx: Rule.RuleContext;
    readonly node: Node;
    readonly status: 'missing' | 'unknown' | 'found';
    constructor(ctx: Rule.RuleContext, node: Node, status: 'missing' | 'unknown' | 'found');
    get isFound(): boolean;
    get isMissing(): boolean;
    get isTrue(): boolean | (RegExp & false) | (RegExp & true);
    ofType(type: Node['type']): boolean;
    getArgument(position: number): Result;
    getProperty(propertyName: string): Result;
    getMemberObject(): Result;
    findInArray(closure: (item: Result) => Result | null | undefined): Result;
    everyStringLiteral(closure: (item: StringLiteral) => boolean): boolean;
    asStringLiterals(): StringLiteral[];
    map<N extends Node, V>(closure: (node: N) => V | null): V | null;
    filter<N extends Node>(closure: (node: N, ctx: Rule.RuleContext) => boolean): Result;
}
export declare function getResultOfExpression(ctx: Rule.RuleContext, node: Node): Result;
