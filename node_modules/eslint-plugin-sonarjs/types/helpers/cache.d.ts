export declare class ComputedCache<K, V, TContext = null> {
    private readonly computeFn;
    private readonly cache;
    constructor(computeFn: (key: K, context?: TContext) => V);
    get(key: K, context?: TContext): V;
    set(key: K, value: V): void;
    has(key: K): boolean;
    delete(key: K): boolean;
    clear(): void;
    get size(): number;
}
