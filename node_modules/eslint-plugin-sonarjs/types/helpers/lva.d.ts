import type { Rule, Scope } from 'eslint';
import type estree from 'estree';
import type { TSESTree } from '@typescript-eslint/utils';
export declare function lva(liveVariablesMap: Map<string, LiveVariables>): void;
export interface ReferenceLike {
    identifier: estree.Identifier | TSESTree.JSXIdentifier;
    from: Scope.Scope;
    resolved: Scope.Variable | null;
    writeExpr: estree.Node | null;
    init: boolean;
    isWrite(): boolean;
    isRead(): boolean;
    isWriteOnly(): boolean;
    isReadOnly(): boolean;
    isReadWrite(): boolean;
}
export declare class LiveVariables {
    constructor(segment: Rule.CodePathSegment);
    segment: Rule.CodePathSegment;
    /**
     * variables that are being read in the block
     */
    gen: Set<Scope.Variable>;
    /**
     * variables that are being written in the block
     */
    kill: Set<Scope.Variable>;
    /**
     * variables needed by this or a successor block and are not killed in this block
     */
    in: Set<Scope.Variable>;
    /**
     * variables needed by successors
     */
    out: Scope.Variable[];
    /**
     * collects references in order they are evaluated, set in JS maintains insertion order
     */
    references: Set<ReferenceLike>;
    add(ref: ReferenceLike): void;
    propagate(liveVariablesMap: Map<string, LiveVariables>): boolean;
}
