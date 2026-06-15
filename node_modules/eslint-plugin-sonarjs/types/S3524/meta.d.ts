export declare const implementation = "original";
export declare const eslintId = "arrow-function-convention";
export * from './config.js';
export declare const schema: {
    readonly type: "array";
    readonly minItems: 0;
    readonly maxItems: 1;
    readonly items: [{
        readonly type: "object";
        readonly properties: {
            readonly requireParameterParentheses: {
                readonly type: "boolean";
            };
            readonly requireBodyBraces: {
                readonly type: "boolean";
            };
        };
        readonly additionalProperties: false;
    }];
};
