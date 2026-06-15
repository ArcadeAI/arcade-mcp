import type { Rule, Scope } from 'eslint';
import type estree from 'estree';
type LiteralValue = string;
declare class AssignedValues extends Set<LiteralValue> {
    type: "AssignedValues";
}
interface UnknownValue {
    type: 'UnknownValue';
}
export type Values = AssignedValues | UnknownValue;
export declare function reachingDefinitions(reachingDefinitionsMap: Map<string, ReachingDefinitions>): void;
export declare class ReachingDefinitions {
    constructor(segment: Rule.CodePathSegment);
    segment: Rule.CodePathSegment;
    in: Map<Scope.Variable, Values>;
    out: Map<Scope.Variable, Values>;
    /**
     * collects references in order they are evaluated, set in JS maintains insertion order
     */
    references: Set<Scope.Reference>;
    add(ref: Scope.Reference): void;
    propagate(reachingDefinitionsMap: Map<string, ReachingDefinitions>): boolean;
    updateProgramState(ref: Scope.Reference, programState: Map<Scope.Variable, Values>): void;
    join(previousOut: Map<Scope.Variable, Values>): void;
}
export declare function resolveAssignedValues(lhsVariable: Scope.Variable, writeExpr: estree.Node | null, assignedValuesMap: Map<Scope.Variable, Values>, scope: Scope.Scope): Values;
export declare function getVariableFromIdentifier(identifier: estree.Identifier, scope: Scope.Scope): Scope.Variable | undefined;
export {};
