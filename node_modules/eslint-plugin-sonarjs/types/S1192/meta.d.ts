export declare const implementation = "original";
export declare const eslintId = "no-duplicate-string";
export * from './config.js';
export declare const hasSecondaries = true;
export declare const schema: {
    readonly type: "array";
    readonly minItems: 0;
    readonly maxItems: 1;
    readonly items: [{
        readonly type: "object";
        readonly properties: {
            readonly threshold: {
                readonly type: "integer";
                readonly minimum: 2;
            };
            readonly ignoreStrings: {
                readonly type: "string";
            };
        };
        readonly additionalProperties: false;
    }];
};
