import type { Rule } from 'eslint';
import type { RulesMeta } from '@eslint/core';
import type estree from 'estree';
/**
 * A symbol fully qualified name, e.g. `aws-cdk-lib.aws_sns.Topic`.
 */
export type FullyQualifiedName = string;
type AwsCdkCallback = {
    functionName?: string;
    methods?: string[];
    callExpression(expr: estree.CallExpression, ctx: Rule.RuleContext, fqn?: string): void;
    newExpression?(expr: estree.NewExpression, ctx: Rule.RuleContext): void;
};
export type AwsCdkConsumer = ((expr: estree.NewExpression, ctx: Rule.RuleContext) => void) | AwsCdkCallback;
type Values = {
    invalid?: any[];
    valid?: any[];
    case_insensitive?: boolean;
};
type ValuesByType = {
    primitives?: Values;
    fqns?: Values;
    customChecker?: (ctx: Rule.RuleContext, node: estree.Node) => boolean;
};
type AwsCdkConsumerMap = {
    [key: FullyQualifiedName]: AwsCdkConsumer;
};
/**
 * A rule template for AWS CDK resources
 *
 * @param mapOrFactory callbacks to invoke when a new expression or a call expression matches a fully qualified name
 * @param meta the rule metadata
 * @returns the instantiated rule module
 */
export declare function AwsCdkTemplate(mapOrFactory: AwsCdkConsumerMap | ((ctx: Rule.RuleContext) => AwsCdkConsumerMap), meta?: RulesMeta): Rule.RuleModule;
/**
 * Function to analyse arguments in a function and check for correct values. It will report if the
 * conditions are not met unless `silent = true`, in which case it will return boolean `true`
 * indicating conditions are not met.
 *
 * @param messageId Array of messageIds or single string if only one messageId is used. When an array is passed,
 *                  first messageId is used for omitted values and second for invalid values.
 * @param needsProps whether default (undefined) values are allowed or if it must be set
 * @param propertyName property name to search in the object (Array of strings for nested props)
 * @param values allowed or disallowed values
 * @param silent whether the function must report or just return conflicting Node when conditions are not met
 * @param position position of the argument to be analysed (3rd argument by default)
 */
export declare function AwsCdkCheckArguments(messageId: string | string[], needsProps: boolean, propertyName: string | string[], values?: ValuesByType, silent?: boolean, position?: number): (expr: estree.NewExpression, ctx: Rule.RuleContext) => estree.Node | undefined;
export declare function getLiteralValue(ctx: Rule.RuleContext, node: estree.Node): estree.Literal | undefined;
export declare function normalizeFQN(fqn?: string | null): string | undefined;
export {};
