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
// https://sonarsource.github.io/rspec/#/rspec/S6303/javascript
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
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const module_js_1 = require("../helpers/module.js");
const ast_js_1 = require("../helpers/ast.js");
const cdk_js_1 = require("../helpers/aws/cdk.js");
const meta = __importStar(require("./generated-meta.js"));
const CfnDBCluster = 'CfnDBCluster';
const CfnDBInstance = 'CfnDBInstance';
const DatabaseCluster = 'DatabaseCluster';
const DatabaseClusterFromSnapshot = 'DatabaseClusterFromSnapshot';
const DatabaseInstance = 'DatabaseInstance';
const DatabaseInstanceReadReplica = 'DatabaseInstanceReadReplica';
exports.rule = (0, cdk_js_1.AwsCdkTemplate)({
    'aws-cdk-lib.aws_rds.CfnDBCluster': checkStorage(CfnDBCluster),
    'aws-cdk-lib.aws_rds.CfnDBInstance': checkStorage(CfnDBInstance),
    'aws-cdk-lib.aws_rds.DatabaseCluster': checkStorage(DatabaseCluster),
    'aws-cdk-lib.aws_rds.DatabaseClusterFromSnapshot': checkStorage(DatabaseClusterFromSnapshot),
    'aws-cdk-lib.aws_rds.DatabaseInstance': checkStorage(DatabaseInstance),
    'aws-cdk-lib.aws_rds.DatabaseInstanceReadReplica': checkStorage(DatabaseInstanceReadReplica),
}, (0, generate_meta_js_1.generateMeta)(meta, {
    messages: {
        unsafe: 'Make sure that using unencrypted storage is safe here.',
        omitted: 'Omitting storageEncrypted disables RDS encryption. Make sure it is safe here.',
    },
}));
const PROPS_ARGUMENT_POSITION = 2;
function checkStorage(storage) {
    return (expr, ctx) => {
        const argument = expr.arguments[PROPS_ARGUMENT_POSITION];
        const props = (0, ast_js_1.getValueOfExpression)(ctx, argument, 'ObjectExpression');
        if (isUnresolved(argument, props)) {
            return;
        }
        if (props === undefined) {
            report(expr.callee, 'omitted');
            return;
        }
        if (isException(storage, props)) {
            return;
        }
        const propertyKey = (0, ast_js_1.getProperty)(props, 'storageEncrypted', ctx);
        if (propertyKey === null) {
            report(props, 'omitted');
        }
        if (!propertyKey) {
            return;
        }
        const propertyValue = (0, ast_js_1.getUniqueWriteUsageOrNode)(ctx, propertyKey.value);
        if ((0, ast_js_1.isFalseLiteral)(propertyValue)) {
            report(propertyKey.value, 'unsafe');
            return;
        }
        function isUnresolved(node, value) {
            return node?.type === 'Identifier' && !(0, ast_js_1.isUndefined)(node) && value === undefined;
        }
        function isException(storage, props) {
            if (![
                DatabaseCluster,
                DatabaseClusterFromSnapshot,
                DatabaseInstance,
                DatabaseInstanceReadReplica,
            ].includes(storage)) {
                return false;
            }
            const exceptionKey = (0, ast_js_1.getProperty)(props, 'storageEncryptionKey', ctx);
            if (exceptionKey == null) {
                return false;
            }
            const exceptionValue = (0, ast_js_1.getUniqueWriteUsageOrNode)(ctx, exceptionKey.value);
            if (exceptionValue.type !== 'NewExpression') {
                return false;
            }
            const fqn = (0, cdk_js_1.normalizeFQN)((0, module_js_1.getFullyQualifiedName)(ctx, exceptionValue.callee));
            return fqn === 'aws_cdk_lib.aws_kms.Key' || fqn === 'aws_cdk_lib.aws_kms.Alias';
        }
        function report(node, messageId) {
            ctx.report({
                messageId,
                node,
            });
        }
    };
}
