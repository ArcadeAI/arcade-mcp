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
// https://sonarsource.github.io/rspec/#/rspec/S6321/javascript
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.rule = void 0;
const cdk_js_1 = require("../helpers/aws/cdk.js");
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const module_js_1 = require("../helpers/module.js");
const ast_js_1 = require("../helpers/ast.js");
const meta = __importStar(require("./generated-meta.js"));
const TYPES_WITH_CONNECTIONS = [
    'aws_cdk_lib.aws_docdb.DatabaseCluster.connections',
    'aws_cdk_lib.aws_lambdaPythonAlpha.PythonFunction.connections',
    'aws_cdk_lib.aws_batchAlpha.ComputeEnvironment.connections',
    'aws_cdk_lib.aws_efs.FileSystem.connections',
    'aws_cdk_lib.aws_lambdaGoAlpha.GoFunction.connections',
    'aws_cdk_lib.aws_ecs.ExternalService.connections',
    'aws_cdk_lib.aws_ecs.FargateService.connections',
    'aws_cdk_lib.aws_ecs.Cluster.connections',
    'aws_cdk_lib.aws_ecs.Ec2Service.connections',
    'aws_cdk_lib.aws_elasticsearch.Domain.connections',
    'aws_cdk_lib.aws_neptuneAlpha.DatabaseCluster.connections',
    'aws_cdk_lib.aws_eks.FargateCluster.connections',
    'aws_cdk_lib.aws_eks.Cluster.connections',
    'aws_cdk_lib.aws_codebuild.PipelineProject.connections',
    'aws_cdk_lib.aws_codebuild.Project.connections',
    'aws_cdk_lib.aws_rds.DatabaseInstance.connections',
    'aws_cdk_lib.aws_rds.DatabaseInstanceReadReplica.connections',
    'aws_cdk_lib.aws_rds.DatabaseCluster.connections',
    'aws_cdk_lib.aws_rds.ServerlessClusterFromSnapshot.connections',
    'aws_cdk_lib.aws_rds.DatabaseProxy.connections',
    'aws_cdk_lib.aws_rds.DatabaseInstanceFromSnapshot.connections',
    'aws_cdk_lib.aws_rds.ServerlessCluster.connections',
    'aws_cdk_lib.aws_rds.DatabaseClusterFromSnapshot.connections',
    'aws_cdk_lib.aws_lambdaNodejs.NodejsFunction.connections',
    'aws_cdk_lib.aws_fsx.LustreFileSystem.connections',
    'aws_cdk_lib.aws_ec2.BastionHostLinux.connections',
    'aws_cdk_lib.aws_ec2.ClientVpnEndpoint.connections',
    'aws_cdk_lib.aws_ec2.Instance.connections',
    'aws_cdk_lib.aws_ec2.LaunchTemplate.connections',
    'aws_cdk_lib.aws_ec2.SecurityGroup.connections',
    'aws_cdk_lib.aws_kinesisfirehoseAlpha.DeliveryStream.connections',
    'aws_cdk_lib.aws_stepfunctionsTasks.SageMakerCreateTrainingJob.connections',
    'aws_cdk_lib.aws_stepfunctionsTasks.SageMakerCreateModel.connections',
    'aws_cdk_lib.aws_stepfunctionsTasks.EcsRunTask.connections',
    'aws_cdk_lib.aws_redshiftAlpha.Cluster.connections',
    'aws_cdk_lib.aws_opensearchservice.Domain.connections',
    'aws_cdk_lib.aws_secretsmanager.HostedRotation.connections',
    'aws_cdk_lib.aws_mskAlpha.Cluster.connections',
    'aws_cdk_lib.triggers.TriggerFunction.connections',
    'aws_cdk_lib.aws_autoscaling.AutoScalingGroup.connections',
    'aws_cdk_lib.aws_syntheticsAlpha.Canary.connections',
    'aws_cdk_lib.aws_cloudfront.experimental.EdgeFunction.connections',
    'aws_cdk_lib.aws_lambda.Function.connections',
    'aws_cdk_lib.aws_lambda.DockerImageFunction.connections',
    'aws_cdk_lib.aws_lambda.SingletonFunction.connections',
    'aws_cdk_lib.aws_lambda.Alias.connections',
    'aws_cdk_lib.aws_lambda.Version.connections',
    'aws_cdk_lib.aws_ec2.Connections',
];
const badPorts = [22, 3389];
const badIpsV4 = new Set(['0.0.0.0/0']);
const badIpsV6 = new Set(['::/0']);
const badFQNProtocols = new Set([
    'aws_cdk_lib.aws_ec2.Protocol.ALL',
    'aws_cdk_lib.aws_ec2.Protocol.TCP',
]);
const badProtocols = new Set(['6', 'tcp', 'TCP']);
const templateCallback = {};
for (const type of TYPES_WITH_CONNECTIONS) {
    templateCallback[`${type}.allowFrom`] = { callExpression: checkAllowFrom };
    templateCallback[`${type}.allowFromAnyIpv4`] = { callExpression: checkAllowFromAnyIpv4 };
}
templateCallback['aws_cdk_lib.aws_ec2.Connections.allowDefaultPortFrom'] = {
    callExpression: (expr, ctx) => {
        if (isBadEc2Peer(ctx, expr.arguments[0])) {
            checkConstructorDefaultPort(ctx, expr);
        }
    },
};
templateCallback['aws_cdk_lib.aws_ec2.Connections.allowDefaultPortFromAnyIpv4'] = {
    callExpression: (expr, ctx) => {
        checkConstructorDefaultPort(ctx, expr);
    },
};
templateCallback['aws_cdk_lib.aws_ec2.SecurityGroup.addIngressRule'] = {
    callExpression: checkAllowFrom,
};
templateCallback['aws_cdk_lib.aws_ec2.CfnSecurityGroup'] = (expr, ctx) => {
    const params = expr.arguments[2];
    const objExpr = (0, ast_js_1.getValueOfExpression)(ctx, params, 'ObjectExpression', true);
    if (!objExpr) {
        return;
    }
    const ingressProp = (0, ast_js_1.getProperty)(objExpr, 'securityGroupIngress', ctx);
    if (!ingressProp) {
        return;
    }
    const arrExpr = (0, ast_js_1.getValueOfExpression)(ctx, ingressProp.value, 'ArrayExpression', true);
    if (arrExpr) {
        for (const ingressGroup of arrExpr.elements) {
            if (ingressGroup) {
                checkIngressObject(ctx, ingressGroup);
            }
        }
    }
};
templateCallback['aws_cdk_lib.aws_ec2.CfnSecurityGroupIngress'] = (expr, ctx) => {
    checkIngressObject(ctx, expr.arguments[2]);
};
exports.rule = (0, cdk_js_1.AwsCdkTemplate)(templateCallback, (0, generate_meta_js_1.generateMeta)(meta, {
    messages: {
        allowFromAnyIpv4: 'Change this method for "allowFrom" and set "other" to a subset of trusted IP addresses.',
        allowFrom: 'Change this IP range to a subset of trusted IP addresses.',
    },
}));
const invalidDefaultPortChecker = (0, cdk_js_1.AwsCdkCheckArguments)('allowFrom', false, 'defaultPort', { customChecker: isBadEc2Port }, true, 0);
function checkConstructorDefaultPort(ctx, node) {
    const newExpr = (0, ast_js_1.getValueOfExpression)(ctx, (0, module_js_1.reduceToIdentifier)(node.callee), 'NewExpression', true);
    if (newExpr && invalidDefaultPortChecker(newExpr, ctx)) {
        ctx.report({ messageId: 'allowFromAnyIpv4', node: node.callee });
    }
}
function checkAllowFrom(expr, ctx) {
    const badPeer = isBadEc2Peer(ctx, expr.arguments[0]);
    const badPort = isBadEc2Port(ctx, expr.arguments[1]);
    if (badPort && badPeer) {
        ctx.report({ messageId: 'allowFrom', node: expr.arguments[0] });
    }
}
function checkAllowFromAnyIpv4(expr, ctx) {
    const badPort = isBadEc2Port(ctx, expr.arguments[0]);
    if (badPort) {
        ctx.report({ messageId: 'allowFromAnyIpv4', node: expr.callee });
    }
}
function checkIngressObject(ctx, node) {
    const objExpr = (0, ast_js_1.getValueOfExpression)(ctx, node, 'ObjectExpression', true);
    if (!objExpr) {
        return;
    }
    const ipPropertyV4 = getPropertyValue(ctx, objExpr, 'cidrIp');
    const ipPropertyV6 = getPropertyValue(ctx, objExpr, 'cidrIpv6');
    const ipProtocol = getPropertyValue(ctx, objExpr, 'ipProtocol')?.value;
    const cidrIpV4 = ipPropertyV4?.value;
    const cidrIpV6 = ipPropertyV6?.value;
    const fromPort = Number.parseInt(getPropertyValue(ctx, objExpr, 'fromPort')?.value);
    const toPort = Number.parseInt(getPropertyValue(ctx, objExpr, 'toPort')?.value);
    if (disallowedIpV4(cidrIpV4) &&
        (ipProtocol === '-1' || (disallowedProtocol(ipProtocol) && disallowedPort(fromPort, toPort)))) {
        ctx.report({ messageId: 'allowFrom', node: ipPropertyV4 });
    }
    if (disallowedIpV6(cidrIpV6) &&
        (ipProtocol === '-1' || (disallowedProtocol(ipProtocol) && disallowedPort(fromPort, toPort)))) {
        ctx.report({ messageId: 'allowFrom', node: ipPropertyV6 });
    }
}
function disallowedPortObject(ctx, node) {
    const objExpr = (0, ast_js_1.getValueOfExpression)(ctx, node, 'ObjectExpression', true);
    if (!objExpr) {
        return false;
    }
    const protocol = (0, ast_js_1.getProperty)(objExpr, 'protocol', ctx);
    if (!protocol) {
        return false;
    }
    const protocolValue = (0, ast_js_1.getUniqueWriteUsageOrNode)(ctx, protocol.value, true);
    if ((0, ast_js_1.isUnresolved)(protocolValue, ctx) || (0, ast_js_1.isUndefined)(protocolValue)) {
        return false;
    }
    const protocolFQN = (0, cdk_js_1.normalizeFQN)((0, module_js_1.getFullyQualifiedName)(ctx, protocolValue));
    if (protocolFQN && badFQNProtocols.has(protocolFQN)) {
        const fromPort = Number.parseInt(getPropertyValue(ctx, objExpr, 'fromPort')?.value);
        const toPort = Number.parseInt(getPropertyValue(ctx, objExpr, 'toPort')?.value);
        return disallowedPort(fromPort, toPort);
    }
    return false;
}
function isBadEc2Peer(ctx, node) {
    const fqn = (0, cdk_js_1.normalizeFQN)((0, module_js_1.getFullyQualifiedName)(ctx, node));
    if (fqn === 'aws_cdk_lib.aws_ec2.Peer.anyIpv4' || fqn === 'aws_cdk_lib.aws_ec2.Peer.anyIpv6') {
        return true;
    }
    if (fqn === 'aws_cdk_lib.aws_ec2.Peer.ipv4') {
        return disallowedIpV4(getArgumentValue(ctx, node)?.value);
    }
    if (fqn === 'aws_cdk_lib.aws_ec2.Peer.ipv6') {
        return disallowedIpV6(getArgumentValue(ctx, node)?.value);
    }
    return false;
}
function isBadEc2Port(ctx, node) {
    const fqn = (0, cdk_js_1.normalizeFQN)((0, module_js_1.getFullyQualifiedName)(ctx, node));
    if (fqn === 'aws_cdk_lib.aws_ec2.Port.allTcp' || fqn === 'aws_cdk_lib.aws_ec2.Port.allTraffic') {
        return true;
    }
    if (fqn === 'aws_cdk_lib.aws_ec2.Port.tcp') {
        return disallowedPort(getArgumentValue(ctx, node)?.value);
    }
    if (fqn === 'aws_cdk_lib.aws_ec2.Port.tcpRange') {
        const startRange = getArgumentValue(ctx, node)?.value;
        const endRange = getArgumentValue(ctx, node, 1)?.value;
        return disallowedPort(startRange, endRange);
    }
    if (fqn === 'aws_cdk_lib.aws_ec2.Port') {
        const portParams = getArgument(ctx, node);
        if (portParams) {
            return disallowedPortObject(ctx, portParams);
        }
    }
    return false;
}
function getArgument(ctx, node, position = 0) {
    if (!node || (0, ast_js_1.isUndefined)(node) || (0, ast_js_1.isUnresolved)(node, ctx)) {
        return undefined;
    }
    const callExpr = (0, ast_js_1.getUniqueWriteUsageOrNode)(ctx, node, true);
    if ((0, ast_js_1.isUnresolved)(callExpr, ctx) ||
        (0, ast_js_1.isUndefined)(callExpr) ||
        (callExpr.type !== 'CallExpression' && callExpr.type !== 'NewExpression')) {
        return undefined;
    }
    const argument = callExpr.arguments[position];
    const argumentValue = (0, ast_js_1.getUniqueWriteUsageOrNode)(ctx, argument, true);
    if ((0, ast_js_1.isUnresolved)(argumentValue, ctx) || (0, ast_js_1.isUndefined)(argumentValue)) {
        return undefined;
    }
    return argumentValue;
}
function getArgumentValue(ctx, node, position = 0) {
    const argument = getArgument(ctx, node, position);
    return argument ? (0, cdk_js_1.getLiteralValue)(ctx, argument) : undefined;
}
function getPropertyValue(ctx, node, propertyName) {
    const property = (0, ast_js_1.getProperty)(node, propertyName, ctx);
    if (!property) {
        return undefined;
    }
    const propertyValue = (0, ast_js_1.getUniqueWriteUsageOrNode)(ctx, property.value, true);
    if ((0, ast_js_1.isUnresolved)(propertyValue, ctx) || (0, ast_js_1.isUndefined)(propertyValue)) {
        return undefined;
    }
    return (0, cdk_js_1.getLiteralValue)(ctx, propertyValue);
}
function disallowedPort(startRange, endRange) {
    if (startRange != null && endRange != null) {
        return badPorts.some(port => port >= startRange && port <= endRange);
    }
    if (startRange != null && endRange == null) {
        return badPorts.includes(startRange);
    }
    return false;
}
function disallowedIpV4(ip) {
    return ip ? badIpsV4.has(ip) : false;
}
function disallowedIpV6(ip) {
    return ip ? badIpsV6.has(ip) : false;
}
function disallowedProtocol(protocol) {
    return protocol ? badProtocols.has(protocol) : false;
}
