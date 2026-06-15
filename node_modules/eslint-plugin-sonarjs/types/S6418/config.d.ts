export declare const fields: [[{
    readonly field: "secretWords";
    readonly description: "Comma separated list of words identifying potential secrets";
    readonly default: "api[_.-]?key,auth,credential,secret,token";
}, {
    readonly field: "randomnessSensibility";
    readonly description: "Minimum shannon entropy threshold of the secret";
    readonly default: 5;
    readonly customDefault: "5.0";
    readonly customForConfiguration: NumberConstructor;
}]];
