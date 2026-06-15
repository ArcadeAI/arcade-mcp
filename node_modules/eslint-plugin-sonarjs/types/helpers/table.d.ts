import type { TSESTree } from '@typescript-eslint/utils';
import type { Rule } from 'eslint';
export type TableCell = {
    isHeader: boolean;
    headers?: string[];
    id?: string;
    node: TSESTree.JSXElement;
    internalNodeId: number;
};
export declare function computeGrid(context: Rule.RuleContext, tree: TSESTree.JSXElement): TableCell[][] | null;
