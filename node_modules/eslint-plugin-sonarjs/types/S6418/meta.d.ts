export declare const implementation = "original";
export declare const eslintId = "no-hardcoded-secrets";
export * from './config.js';
export declare const schema: {
    readonly type: "array";
    readonly minItems: 0;
    readonly maxItems: 1;
    readonly items: [{
        readonly type: "object";
        readonly properties: {
            readonly secretWords: {
                readonly type: "string";
            };
            readonly randomnessSensibility: {
                readonly type: "number";
            };
        };
        readonly additionalProperties: false;
    }];
};
