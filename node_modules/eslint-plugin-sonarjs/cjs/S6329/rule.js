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
// https://sonarsource.github.io/rspec/#/rspec/S6329/javascript
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
const result_js_1 = require("../helpers/result.js");
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const module_js_1 = require("../helpers/module.js");
const ast_js_1 = require("../helpers/ast.js");
const meta = __importStar(require("./generated-meta.js"));
const PROPERTIES_POSITION = 2;
const PRIVATE_SUBNETS = new Set([
    'aws_cdk_lib.aws_ec2.SubnetType.PRIVATE_ISOLATED',
    'aws_cdk_lib.aws_ec2.SubnetType.PRIVATE_WITH_EGRESS',
    'aws_cdk_lib.aws_ec2.SubnetType.PRIVATE_WITH_NAT',
]);
const PUBLIC_SUBNET = 'aws_cdk_lib.aws_ec2.SubnetType.PUBLIC';
exports.rule = (0, cdk_js_1.AwsCdkTemplate)({
    'aws-cdk-lib.aws-ec2.Instance': (0, cdk_js_1.AwsCdkCheckArguments)('publicNetwork', false, ['vpcSubnets', 'subnetType'], { fqns: { invalid: [PUBLIC_SUBNET] } }),
    'aws-cdk-lib.aws-ec2.CfnInstance': checkCfnInstance,
    'aws-cdk-lib.aws_rds.DatabaseInstance': checkDatabaseInstance,
    'aws-cdk-lib.aws_rds.CfnDBInstance': (0, cdk_js_1.AwsCdkCheckArguments)('publicNetwork', false, 'publiclyAccessible', { primitives: { invalid: [true] } }),
    'aws-cdk-lib.aws_dms.CfnReplicationInstance': (0, cdk_js_1.AwsCdkCheckArguments)('publicNetwork', true, 'publiclyAccessible', { primitives: { invalid: [true] } }),
}, (0, generate_meta_js_1.generateMeta)(meta, {
    messages: {
        publicNetwork: 'Make sure allowing public network access is safe here.',
    },
}));
function checkCfnInstance(expr, ctx) {
    const properties = (0, result_js_1.getResultOfExpression)(ctx, expr).getArgument(PROPERTIES_POSITION);
    const networkInterfaces = properties.getProperty('networkInterfaces');
    const sensitiveNetworkInterface = networkInterfaces.findInArray(result => getSensitiveNetworkInterface(result, ctx));
    if (sensitiveNetworkInterface.isFound) {
        ctx.report({
            messageId: 'publicNetwork',
            node: sensitiveNetworkInterface.node,
        });
    }
}
function getSensitiveNetworkInterface(networkInterface, ctx) {
    const associatePublicIpAddress = networkInterface.getProperty('associatePublicIpAddress');
    if (associatePublicIpAddress.isTrue && !isFoundPrivateSubnet(networkInterface, ctx)) {
        return associatePublicIpAddress;
    }
    else {
        return null;
    }
}
function isFoundPrivateSubnet(networkInterface, ctx) {
    const subnetId = networkInterface.getProperty('subnetId');
    const selectSubnetsCall = getSelectSubnetsCall(subnetId);
    const argument = selectSubnetsCall.getArgument(0);
    const subnetType = argument.getProperty('subnetType');
    return subnetType.isFound && isPrivateSubnet(subnetType.node, ctx);
}
function getSelectSubnetsCall(subnetId) {
    let current = subnetId;
    while (current.ofType('MemberExpression')) {
        current = current.getMemberObject();
    }
    return current.filter(n => n.type === 'CallExpression' && (0, ast_js_1.isCallingMethod)(n, 1, 'selectSubnets'));
}
function checkDatabaseInstance(expr, ctx) {
    const properties = (0, result_js_1.getResultOfExpression)(ctx, expr).getArgument(PROPERTIES_POSITION);
    const vpcSubnets = properties.getProperty('vpcSubnets');
    const subnetType = vpcSubnets.getProperty('subnetType');
    const publiclyAccessible = properties.getProperty('publiclyAccessible');
    if (subnetType.isFound && isPrivateSubnet(subnetType.node, ctx)) {
        return;
    }
    if (publiclyAccessible.isTrue && subnetType.isFound && isPublicSubnet(subnetType.node, ctx)) {
        ctx.report({
            messageId: 'publicNetwork',
            node: publiclyAccessible.node,
        });
    }
    else if (!publiclyAccessible.isFound &&
        subnetType.isFound &&
        isPublicSubnet(subnetType.node, ctx)) {
        ctx.report({
            messageId: 'publicNetwork',
            node: subnetType.node,
        });
    }
}
function isPrivateSubnet(node, ctx) {
    const subnet = (0, module_js_1.getFullyQualifiedName)(ctx, node)?.replaceAll('-', '_');
    return subnet !== undefined && PRIVATE_SUBNETS.has(subnet);
}
function isPublicSubnet(node, ctx) {
    return PUBLIC_SUBNET === (0, module_js_1.getFullyQualifiedName)(ctx, node)?.replaceAll('-', '_');
}
