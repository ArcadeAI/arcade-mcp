export declare const implementation = "original";
export declare const eslintId = "no-hardcoded-passwords";
export * from './config.js';
export declare const schema: {
    readonly type: "array";
    readonly minItems: 0;
    readonly maxItems: 1;
    readonly items: [{
        readonly type: "object";
        readonly properties: {
            readonly passwordWords: {
                readonly type: "array";
                readonly items: {
                    readonly type: "string";
                };
            };
        };
        readonly additionalProperties: false;
    }];
};
