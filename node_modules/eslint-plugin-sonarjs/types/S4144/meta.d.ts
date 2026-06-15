export declare const implementation = "original";
export declare const eslintId = "no-identical-functions";
export * from './config.js';
export declare const hasSecondaries = true;
export declare const schema: {
    readonly type: "array";
    readonly minItems: 0;
    readonly maxItems: 1;
    readonly items: [{
        readonly type: "integer";
        readonly minimum: 3;
    }];
};
