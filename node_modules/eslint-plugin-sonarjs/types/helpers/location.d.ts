import type estree from 'estree';
import type { AST, Rule } from 'eslint';
import type { TSESLint, TSESTree } from '@typescript-eslint/utils';
export type LocationHolder = AST.Token | TSESTree.Node | estree.Node | {
    loc: AST.SourceLocation;
};
/**
 * An issue location for secondary locations in rules.
 *
 * Note: This is intentionally defined here (not imported from shared) to keep
 * the rules folder self-contained for the eslint-plugin build.
 *
 * @param line the issue starting line
 * @param column the issue starting column
 * @param endLine the issue ending line
 * @param endColumn the issue ending column
 * @param message the issue message
 */
export interface IssueLocation {
    line: number;
    column: number;
    endLine: number;
    endColumn: number;
    message?: string;
}
export interface EncodedMessage {
    message: string;
    cost?: number;
    secondaryLocations: IssueLocation[];
}
export declare function encodeContents(message: string, secondaryLocations?: IssueLocation[], cost?: number): string;
export declare function toSecondaryLocation(startLoc: LocationHolder): IssueLocation;
export declare function toSecondaryLocation(startLoc: LocationHolder, message: string): IssueLocation;
export declare function toSecondaryLocation(startLoc: LocationHolder, endLoc: LocationHolder): IssueLocation;
export declare function toSecondaryLocation(startLoc: LocationHolder, endLoc: LocationHolder, message: string): IssueLocation;
/**
 * Wrapper for `context.report`, supporting secondary locations and cost.
 * Encode those extra information in the issue message when rule is executed
 * in Sonar* environment.
 */
export declare function report(context: Rule.RuleContext, reportDescriptor: Rule.ReportDescriptor, secondaryLocations?: IssueLocation[], cost?: number): void;
export declare function expandMessage(message: string, reportDescriptorData: Record<string, unknown> | undefined): string;
/**
 * Returns a location of the "main" function token:
 * - function name for a function declaration, method or accessor
 * - "function" keyword for a function expression
 * - "=>" for an arrow function
 */
export declare function getMainFunctionTokenLocation<T = string>(fn: TSESTree.FunctionLike, parent: TSESTree.Node | undefined, context: TSESLint.RuleContext<string, T[]>): TSESTree.SourceLocation;
export declare function getFirstTokenAfter<T = string>(node: TSESTree.Node, context: TSESLint.RuleContext<string, T[]>): TSESLint.AST.Token | null;
export declare function getFirstToken<T = string>(node: TSESTree.Node, context: TSESLint.RuleContext<string, T[]>): TSESLint.AST.Token;
