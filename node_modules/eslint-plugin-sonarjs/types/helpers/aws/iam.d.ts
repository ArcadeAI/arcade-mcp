import type { Node } from 'estree';
import type { Rule } from 'eslint';
import { type Result } from '../result.js';
import { type StringLiteral } from '../ast.js';
import type { RulesMeta } from '@eslint/core';
export interface PolicyCheckerOptions {
    effect: {
        property: string;
        type: 'FullyQualifiedName' | 'string';
        allowValue: string;
    };
    actions: {
        property: string;
        anyValues?: string[];
    };
    resources: {
        property: string;
    };
    conditions: {
        property: string;
    };
    principals: {
        property: string;
        type: 'FullyQualifiedName' | 'json';
        anyValues?: string[];
    };
}
type StatementChecker = (expr: Node, ctx: Rule.RuleContext, options: PolicyCheckerOptions) => void;
export declare function AwsIamPolicyTemplate(statementChecker: StatementChecker, meta: RulesMeta): Rule.RuleModule;
export declare function getSensitiveEffect(properties: Result, ctx: Rule.RuleContext, options: PolicyCheckerOptions): Result;
export declare function isAnyLiteral(literal: StringLiteral): boolean;
export {};
