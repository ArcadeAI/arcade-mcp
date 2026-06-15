import type estree from 'estree';
import * as regexpp from '@eslint-community/regexpp';
import type { Rule } from 'eslint';
export declare function getParsedRegex(node: estree.Node, context: Rule.RuleContext): regexpp.AST.RegExpLiteral | null;
export declare function getPatternFromNode(node: estree.Node, context: Rule.RuleContext): {
    pattern: string;
    flags: string;
} | null;
