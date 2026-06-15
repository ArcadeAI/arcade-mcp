export declare const implementation = "original";
export declare const eslintId = "cognitive-complexity";
export * from './config.js';
export declare const hasSecondaries = true;
export declare const schema: {
    readonly type: "array";
    readonly minItems: 0;
    readonly maxItems: 2;
    readonly items: [{
        readonly oneOf: [{
            readonly type: "integer";
            readonly minimum: 0;
        }, {
            readonly type: "string";
            readonly enum: ["silence-issues"];
        }];
    }, {
        readonly type: "string";
        readonly enum: ["silence-issues"];
    }];
};
