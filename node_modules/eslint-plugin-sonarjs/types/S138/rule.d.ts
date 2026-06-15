import type { Rule } from 'eslint';
import type estree from 'estree';
export declare const rule: Rule.RuleModule;
export declare function getLocsNumber(loc: estree.SourceLocation, lines: string[], commentLineNumbers: Map<number, estree.Comment>): number;
export declare function getCommentLineNumbers(comments: estree.Comment[]): Map<number, estree.Comment>;
