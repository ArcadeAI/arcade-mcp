export declare const implementation = "original";
export declare const eslintId = "comment-regex";
export * from './config.js';
export declare const schema: {
    readonly type: "array";
    readonly minItems: 0;
    readonly maxItems: 1;
    readonly items: [{
        readonly type: "object";
        readonly properties: {
            readonly regularExpression: {
                readonly type: "string";
            };
            readonly message: {
                readonly type: "string";
            };
            readonly flags: {
                readonly type: "string";
            };
        };
        readonly additionalProperties: false;
    }];
};
