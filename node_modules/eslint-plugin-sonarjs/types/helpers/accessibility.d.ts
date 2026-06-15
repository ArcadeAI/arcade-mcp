import type { TSESTree } from '@typescript-eslint/utils';
import type { Rule } from 'eslint';
export declare function isPresentationTable(context: Rule.RuleContext, node: TSESTree.JSXOpeningElement): boolean;
export declare const getElementType: (context: Rule.RuleContext) => ((node: TSESTree.JSXOpeningElement) => string);
