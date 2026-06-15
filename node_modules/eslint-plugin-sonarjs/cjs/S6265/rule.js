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
// https://sonarsource.github.io/rspec/#/rspec/S6265/javascript
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
const s3_js_1 = require("../helpers/aws/s3.js");
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const module_js_1 = require("../helpers/module.js");
const ast_js_1 = require("../helpers/ast.js");
const collection_js_1 = require("../helpers/collection.js");
const merger_js_1 = require("../helpers/decorators/merger.js");
const cdk_js_1 = require("../helpers/aws/cdk.js");
const location_js_1 = require("../helpers/location.js");
const meta = __importStar(require("./generated-meta.js"));
const messages = {
    accessLevel: (param) => `Make sure granting ${param} access is safe here.`,
    unrestricted: 'Make sure allowing unrestricted access to objects from this bucket is safe here.',
};
const ACCESS_CONTROL_KEY = 'accessControl';
const INVALID_ACCESS_CONTROL_VALUES = ['PUBLIC_READ', 'PUBLIC_READ_WRITE', 'AUTHENTICATED_READ'];
const PUBLIC_READ_ACCESS_KEY = 'publicReadAccess';
const INVALID_PUBLIC_READ_ACCESS_VALUE = true;
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta),
    create(context) {
        return (0, merger_js_1.mergeRules)(s3BucketConstructorRule.create(context), s3BucketDeploymentConstructorRule.create(context), handleGrantPublicAccess.create(context));
    },
};
const s3BucketConstructorRule = (0, s3_js_1.S3BucketTemplate)((bucketConstructor, context) => {
    for (const value of INVALID_ACCESS_CONTROL_VALUES) {
        checkConstantParam(context, bucketConstructor, ACCESS_CONTROL_KEY, [
            'BucketAccessControl',
            value,
        ]);
    }
    checkBooleanParam(context, bucketConstructor, PUBLIC_READ_ACCESS_KEY, INVALID_PUBLIC_READ_ACCESS_VALUE);
});
const s3BucketDeploymentConstructorRule = {
    create(context) {
        return {
            NewExpression: (node) => {
                if ((0, s3_js_1.isS3BucketDeploymentConstructor)(context, node)) {
                    for (const value of INVALID_ACCESS_CONTROL_VALUES) {
                        checkConstantParam(context, node, ACCESS_CONTROL_KEY, ['BucketAccessControl', value]);
                    }
                }
            },
        };
    },
};
function checkBooleanParam(context, bucketConstructor, propName, propValue) {
    const property = (0, s3_js_1.getBucketProperty)(context, bucketConstructor, propName);
    if (property == null) {
        return;
    }
    const propertyLiteralValue = (0, ast_js_1.getValueOfExpression)(context, property.value, 'Literal');
    if (propertyLiteralValue?.value === propValue) {
        const secondary = (0, s3_js_1.findPropagatedSetting)(property, propertyLiteralValue);
        (0, location_js_1.report)(context, {
            message: messages.unrestricted,
            node: property,
        }, secondary ? [secondary] : []);
    }
}
function checkConstantParam(context, bucketConstructor, propName, paramQualifiers) {
    const property = (0, s3_js_1.getBucketProperty)(context, bucketConstructor, propName);
    if (property == null) {
        return;
    }
    const propertyLiteralValue = (0, ast_js_1.getValueOfExpression)(context, property.value, 'MemberExpression');
    if (propertyLiteralValue !== undefined &&
        (0, cdk_js_1.normalizeFQN)((0, module_js_1.getFullyQualifiedName)(context, propertyLiteralValue)) ===
            `aws_cdk_lib.aws_s3.${paramQualifiers.join('.')}`) {
        const secondary = (0, s3_js_1.findPropagatedSetting)(property, propertyLiteralValue);
        (0, location_js_1.report)(context, {
            message: messages.accessLevel((0, collection_js_1.last)(paramQualifiers)),
            node: property,
        }, secondary ? [secondary] : []);
    }
}
const handleGrantPublicAccess = {
    create(context) {
        return {
            CallExpression: (node) => {
                if (!(0, ast_js_1.isMethodCall)(node)) {
                    return;
                }
                const { object, property } = node.callee;
                const isGrantPublicAccessMethodCall = (0, ast_js_1.isIdentifier)(property, 'grantPublicAccess');
                if (!isGrantPublicAccessMethodCall) {
                    return;
                }
                const variableAssignment = (0, ast_js_1.getUniqueWriteUsageOrNode)(context, object);
                const isS3bucketInstance = variableAssignment.type === 'NewExpression' &&
                    (0, s3_js_1.isS3BucketConstructor)(context, variableAssignment);
                if (!isS3bucketInstance) {
                    return;
                }
                (0, location_js_1.report)(context, {
                    message: messages.unrestricted,
                    node: property,
                });
            },
        };
    },
};
