"use strict";
/*
 * SonarQube JavaScript Plugin
 * Copyright (C) SonarSource Sàrl
 * mailto:info AT sonarsource DOT com
 *
 * You can redistribute and/or modify this program under the terms of
 * the Sonar Source-Available License Version 1, as published by SonarSource Sàrl.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
 * See the Sonar Source-Available License for more details.
 *
 * You should have received a copy of the Sonar Source-Available License
 * along with this program; if not, see https://sonarsource.com/license/ssal/
 */
// https://sonarsource.github.io/rspec/#/rspec/S5332/javascript
Object.defineProperty(exports, "__esModule", { value: true });
exports.rule = void 0;
const cdk_js_1 = require("../helpers/aws/cdk.js");
const sensitivePorts = [80, 8080, 8000, 8008];
exports.rule = (0, cdk_js_1.AwsCdkTemplate)({
    'aws-cdk-lib.aws_elasticache.CfnReplicationGroup': (0, cdk_js_1.AwsCdkCheckArguments)('replicationGroup', true, 'transitEncryptionEnabled', { primitives: { invalid: [false] } }),
    'aws-cdk-lib.aws_kinesis.Stream': (0, cdk_js_1.AwsCdkCheckArguments)('streamEncryptionDisabled', false, 'encryption', { fqns: { invalid: ['aws_cdk_lib.aws_kinesis.StreamEncryption.UNENCRYPTED'] } }),
    'aws-cdk-lib.aws_kinesis.CfnStream': (0, cdk_js_1.AwsCdkCheckArguments)('streamEncryptionDisabled', true, 'streamEncryption'),
    'aws-cdk-lib.aws_elasticloadbalancing.LoadBalancer': {
        callExpression: (0, cdk_js_1.AwsCdkCheckArguments)('noSSLTLS', false, 'externalProtocol', {
            fqns: {
                invalid: [
                    'aws-cdk-lib.aws_elasticloadbalancing.LoadBalancingProtocol.TCP',
                    'aws-cdk-lib.aws_elasticloadbalancing.LoadBalancingProtocol.HTTP',
                ],
            },
        }, false, 0),
        functionName: 'addListener',
        newExpression: (0, cdk_js_1.AwsCdkCheckArguments)('noSSLTLS', false, ['listeners', 'externalProtocol'], {
            fqns: {
                invalid: [
                    'aws-cdk-lib.aws_elasticloadbalancing.LoadBalancingProtocol.TCP',
                    'aws-cdk-lib.aws_elasticloadbalancing.LoadBalancingProtocol.HTTP',
                ],
            },
        }),
    },
    'aws-cdk-lib.aws_elasticloadbalancing.CfnLoadBalancer': (0, cdk_js_1.AwsCdkCheckArguments)('noSSLTLS', false, ['listeners', 'protocol'], { primitives: { invalid: ['tcp', 'http'], case_insensitive: true } }),
    'aws-cdk-lib.aws_elasticloadbalancingv2.ApplicationLoadBalancer': {
        callExpression: httpOrSensitivePort(1),
        functionName: 'addListener',
    },
    'aws-cdk-lib.aws_elasticloadbalancingv2.ApplicationListener': httpOrSensitivePort(2),
    'aws-cdk-lib.aws_elasticloadbalancingv2.NetworkLoadBalancer': {
        callExpression: (expr, ctx) => {
            const httpProtocol = (0, cdk_js_1.AwsCdkCheckArguments)('noSSLTLS', false, 'protocol', {
                fqns: {
                    invalid: [
                        'aws-cdk-lib.aws_elasticloadbalancingv2.Protocol.HTTP',
                        'aws-cdk-lib.aws_elasticloadbalancingv2.Protocol.TCP',
                        'aws-cdk-lib.aws_elasticloadbalancingv2.Protocol.UDP',
                        'aws-cdk-lib.aws_elasticloadbalancingv2.Protocol.TCP_UDP',
                    ],
                },
            }, true, 1);
            const node = httpProtocol(expr, ctx);
            if (node) {
                ctx.report({ messageId: 'noSSLTLS', node });
            }
            else {
                const missingProtocol = (0, cdk_js_1.AwsCdkCheckArguments)('noSSLTLS', true, 'protocol', undefined, true, 1);
                if (missingProtocol(expr, ctx)) {
                    const certificatesChecker = (0, cdk_js_1.AwsCdkCheckArguments)('noSSLTLS', true, 'certificates', undefined, true, 1);
                    const portNode = certificatesChecker(expr, ctx);
                    if (portNode) {
                        ctx.report({ messageId: 'noSSLTLS', node: portNode });
                    }
                }
            }
        },
        functionName: 'addListener',
    },
    'aws-cdk-lib.aws_elasticloadbalancingv2.NetworkListener': (expr, ctx) => {
        const httpProtocol = (0, cdk_js_1.AwsCdkCheckArguments)('noSSLTLS', false, 'protocol', {
            fqns: {
                invalid: [
                    'aws-cdk-lib.aws_elasticloadbalancingv2.Protocol.TCP',
                    'aws-cdk-lib.aws_elasticloadbalancingv2.Protocol.UDP',
                    'aws-cdk-lib.aws_elasticloadbalancingv2.Protocol.TCP_UDP',
                ],
            },
        }, true);
        const node = httpProtocol(expr, ctx);
        if (node) {
            ctx.report({ messageId: 'noSSLTLS', node });
        }
        else {
            const missingProtocol = (0, cdk_js_1.AwsCdkCheckArguments)('noSSLTLS', true, 'protocol', undefined, true);
            if (missingProtocol(expr, ctx)) {
                const certificatesChecker = (0, cdk_js_1.AwsCdkCheckArguments)('noSSLTLS', true, 'certificates', undefined, true);
                const portNode = certificatesChecker(expr, ctx);
                if (portNode) {
                    ctx.report({ messageId: 'noSSLTLS', node: portNode });
                }
            }
        }
    },
    'aws-cdk-lib.aws_elasticloadbalancingv2.CfnListener': (0, cdk_js_1.AwsCdkCheckArguments)('noSSLTLS', false, 'protocol', { primitives: { invalid: ['HTTP', 'TCP', 'UDP', 'TCP_UDP'], case_insensitive: true } }),
}, {
    messages: {
        replicationGroup: 'Make sure that disabling transit encryption is safe here.',
        noSSLTLS: 'Make sure that using network protocols without an SSL/TLS underlay is safe here.',
        streamEncryptionDisabled: 'Make sure that disabling stream encryption is safe here.',
    },
});
function httpOrSensitivePort(position) {
    return function (expr, ctx) {
        const httpProtocol = (0, cdk_js_1.AwsCdkCheckArguments)('noSSLTLS', false, 'protocol', { fqns: { invalid: ['aws-cdk-lib.aws_elasticloadbalancingv2.ApplicationProtocol.HTTP'] } }, true, position);
        const node = httpProtocol(expr, ctx);
        if (node) {
            ctx.report({ messageId: 'noSSLTLS', node });
        }
        else {
            const missingProtocol = (0, cdk_js_1.AwsCdkCheckArguments)('noSSLTLS', true, 'protocol', undefined, true, position);
            if (missingProtocol(expr, ctx)) {
                const portChecker = (0, cdk_js_1.AwsCdkCheckArguments)('noSSLTLS', false, 'port', { primitives: { invalid: sensitivePorts } }, true, position);
                const portNode = portChecker(expr, ctx);
                if (portNode) {
                    ctx.report({ messageId: 'noSSLTLS', node: portNode });
                }
            }
        }
    };
}
