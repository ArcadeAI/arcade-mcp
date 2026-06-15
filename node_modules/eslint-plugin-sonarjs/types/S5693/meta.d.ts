export declare const implementation = "original";
export declare const eslintId = "content-length";
export * from './config.js';
export declare const schema: {
    readonly type: "array";
    readonly minItems: 0;
    readonly maxItems: 1;
    readonly items: [{
        readonly type: "object";
        readonly properties: {
            readonly fileUploadSizeLimit: {
                readonly type: "integer";
            };
            readonly standardSizeLimit: {
                readonly type: "integer";
            };
        };
        readonly additionalProperties: false;
    }];
};
