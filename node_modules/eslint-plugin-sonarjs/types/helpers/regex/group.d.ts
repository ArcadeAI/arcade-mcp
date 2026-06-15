import type estree from 'estree';
export interface GroupReference {
    raw: string;
    value: string;
}
export declare function extractReferences(node: estree.Node): GroupReference[];
