import type estree from 'estree';
/** Returns a list of statements corresponding to a `if - else if - else` chain */
export declare function collectIfBranches(node: estree.IfStatement): {
    branches: estree.Statement[];
    endsWithElse: boolean;
};
/** Returns a list of `switch` clauses (both `case` and `default`) */
export declare function collectSwitchBranches(node: estree.SwitchStatement): {
    branches: estree.Statement[][];
    endsWithDefault: boolean;
};
/** Excludes the break statement from the list */
export declare function takeWithoutBreak(nodes: estree.Statement[]): estree.Statement[];
