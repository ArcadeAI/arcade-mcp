export declare const implementation = "original";
export declare const eslintId = "file-header";
export * from './config.js';
export declare const schema: {
    readonly type: "array";
    readonly minItems: 0;
    readonly maxItems: 1;
    readonly items: [{
        readonly type: "object";
        readonly properties: {
            readonly headerFormat: {
                readonly type: "string";
            };
            readonly isRegularExpression: {
                readonly type: "boolean";
            };
        };
        readonly additionalProperties: false;
    }];
};
