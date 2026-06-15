export declare const implementation = "original";
export declare const eslintId = "max-lines";
export * from './config.js';
export declare const schema: {
    readonly type: "array";
    readonly minItems: 0;
    readonly maxItems: 1;
    readonly items: [{
        readonly type: "object";
        readonly properties: {
            readonly maximum: {
                readonly type: "integer";
            };
        };
        readonly additionalProperties: false;
    }];
};
