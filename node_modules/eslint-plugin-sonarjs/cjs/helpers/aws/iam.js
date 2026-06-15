"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.AwsIamPolicyTemplate = AwsIamPolicyTemplate;
exports.getSensitiveEffect = getSensitiveEffect;
exports.isAnyLiteral = isAnyLiteral;
const cdk_js_1 = require("./cdk.js");
const result_js_1 = require("../result.js");
const ast_js_1 = require("../ast.js");
const module_js_1 = require("../module.js");
const PROPERTIES_POSITION = 0;
const POLICY_DOCUMENT_STATEMENT_PROPERTY = 'Statement';
const ARN_PRINCIPAL = 'aws_cdk_lib.aws_iam.ArnPrincipal';
const STAR_PRINCIPAL = 'aws_cdk_lib.aws_iam.StarPrincipal';
const ANY_PRINCIPAL = 'aws_cdk_lib.aws_iam.AnyPrincipal';
const ANY_LITERAL = '*';
const PROPERTIES_OPTIONS = {
    effect: {
        property: 'effect',
        type: 'FullyQualifiedName',
        allowValue: 'aws_cdk_lib.aws_iam.Effect.ALLOW',
    },
    actions: {
        property: 'actions',
    },
    resources: {
        property: 'resources',
    },
    conditions: {
        property: 'conditions',
    },
    principals: {
        property: 'principals',
        type: 'FullyQualifiedName',
        anyValues: [STAR_PRINCIPAL, ANY_PRINCIPAL, ARN_PRINCIPAL],
    },
};
const JSON_OPTIONS = {
    effect: {
        property: 'Effect',
        type: 'string',
        allowValue: 'Allow',
    },
    actions: {
        property: 'Action',
    },
    resources: {
        property: 'Resource',
    },
    conditions: {
        property: 'Condition',
    },
    principals: {
        property: 'Principal',
        type: 'json',
    },
};
function AwsIamPolicyTemplate(statementChecker, meta) {
    return (0, cdk_js_1.AwsCdkTemplate)({
        'aws-cdk-lib.aws-iam.PolicyStatement': {
            newExpression: policyStatementChecker(statementChecker, PROPERTIES_OPTIONS),
            functionName: 'fromJson',
            callExpression: policyStatementChecker(statementChecker, JSON_OPTIONS),
        },
        'aws-cdk-lib.aws-iam.PolicyDocument': {
            functionName: 'fromJson',
            callExpression: policyDocumentChecker(statementChecker, JSON_OPTIONS),
        },
    }, meta);
}
function getSensitiveEffect(properties, ctx, options) {
    const effect = properties.getProperty(options.effect.property);
    return effect.filter(node => {
        if (options.effect.type === 'FullyQualifiedName') {
            const fullyQualifiedName = (0, cdk_js_1.normalizeFQN)((0, module_js_1.getFullyQualifiedName)(ctx, node));
            return fullyQualifiedName === options.effect.allowValue;
        }
        else {
            return (0, ast_js_1.isStringLiteral)(node) && node.value === options.effect.allowValue;
        }
    });
}
function isAnyLiteral(literal) {
    return literal.value === ANY_LITERAL;
}
function policyDocumentChecker(statementChecker, options) {
    return (expr, ctx) => {
        const call = (0, result_js_1.getResultOfExpression)(ctx, expr);
        const properties = call.getArgument(PROPERTIES_POSITION);
        const statements = properties.getProperty(POLICY_DOCUMENT_STATEMENT_PROPERTY);
        if (statements.isFound) {
            for (const node of (0, ast_js_1.flattenArgs)(ctx, [statements.node])) {
                statementChecker(node, ctx, options);
            }
        }
    };
}
function policyStatementChecker(statementChecker, options) {
    return (expr, ctx) => {
        const call = (0, result_js_1.getResultOfExpression)(ctx, expr);
        const properties = call.getArgument(PROPERTIES_POSITION);
        if (properties.isFound) {
            statementChecker(properties.node, ctx, options);
        }
    };
}
