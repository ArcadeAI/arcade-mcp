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
// https://sonarsource.github.io/rspec/#/rspec/S6281/javascript
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
const cdk_js_1 = require("../helpers/aws/cdk.js");
const location_js_1 = require("../helpers/location.js");
const meta = __importStar(require("./generated-meta.js"));
const BLOCK_PUBLIC_ACCESS_KEY = 'blockPublicAccess';
const BLOCK_PUBLIC_ACCESS_PROPERTY_KEYS = [
    'blockPublicAcls',
    'blockPublicPolicy',
    'ignorePublicAcls',
    'restrictPublicBuckets',
];
const messages = {
    omitted: 'No Public Access Block configuration prevents public ACL/policies ' +
        'to be set on this S3 bucket. Make sure it is safe here.',
    public: 'Make sure allowing public ACL/policies to be set is safe here.',
};
exports.rule = (0, s3_js_1.S3BucketTemplate)((bucket, context) => {
    const blockPublicAccess = (0, s3_js_1.getBucketProperty)(context, bucket, BLOCK_PUBLIC_ACCESS_KEY);
    if (blockPublicAccess == null) {
        (0, location_js_1.report)(context, {
            message: messages['omitted'],
            node: bucket.callee,
        });
    }
    else {
        checkBlockPublicAccessValue(blockPublicAccess);
        checkBlockPublicAccessConstructor(blockPublicAccess);
    }
    /** Checks `blockPublicAccess: s3.BlockPublicAccess.BLOCK_ACLS` sensitive pattern */
    function checkBlockPublicAccessValue(blockPublicAccess) {
        const blockPublicAccessMember = (0, ast_js_1.getValueOfExpression)(context, blockPublicAccess.value, 'MemberExpression');
        if (blockPublicAccessMember !== undefined &&
            (0, cdk_js_1.normalizeFQN)((0, module_js_1.getFullyQualifiedName)(context, blockPublicAccessMember)) ===
                'aws_cdk_lib.aws_s3.BlockPublicAccess.BLOCK_ACLS') {
            const propagated = (0, s3_js_1.findPropagatedSetting)(blockPublicAccess, blockPublicAccessMember);
            (0, location_js_1.report)(context, {
                message: messages['public'],
                node: blockPublicAccess,
            }, propagated ? [propagated] : []);
        }
    }
    /** Checks `blockPublicAccess: new s3.BlockPublicAccess({...})` sensitive pattern */
    function checkBlockPublicAccessConstructor(blockPublicAccess) {
        const blockPublicAccessNew = (0, ast_js_1.getValueOfExpression)(context, blockPublicAccess.value, 'NewExpression');
        if (blockPublicAccessNew !== undefined &&
            isS3BlockPublicAccessConstructor(blockPublicAccessNew)) {
            const blockPublicAccessConfig = (0, ast_js_1.getValueOfExpression)(context, blockPublicAccessNew.arguments[0], 'ObjectExpression');
            if (blockPublicAccessConfig === undefined) {
                (0, location_js_1.report)(context, {
                    message: messages['omitted'],
                    node: blockPublicAccessNew,
                });
            }
            else {
                for (const key of BLOCK_PUBLIC_ACCESS_PROPERTY_KEYS) {
                    checkBlockPublicAccessConstructorProperty(blockPublicAccessConfig, key);
                }
            }
        }
        function checkBlockPublicAccessConstructorProperty(blockPublicAccessConfig, key) {
            const blockPublicAccessProperty = blockPublicAccessConfig.properties.find(property => (0, ast_js_1.isProperty)(property) && (0, ast_js_1.isIdentifier)(property.key, key));
            if (blockPublicAccessProperty !== undefined) {
                const blockPublicAccessValue = (0, ast_js_1.getValueOfExpression)(context, blockPublicAccessProperty.value, 'Literal');
                if (blockPublicAccessValue?.value === false) {
                    const propagated = (0, s3_js_1.findPropagatedSetting)(blockPublicAccessProperty, blockPublicAccessValue);
                    (0, location_js_1.report)(context, {
                        message: messages['public'],
                        node: blockPublicAccessProperty,
                    }, propagated ? [propagated] : []);
                }
            }
        }
        function isS3BlockPublicAccessConstructor(expr) {
            return (expr.callee.type === 'MemberExpression' &&
                (0, cdk_js_1.normalizeFQN)((0, module_js_1.getFullyQualifiedName)(context, expr.callee)) ===
                    'aws_cdk_lib.aws_s3.BlockPublicAccess');
        }
    }
}, (0, generate_meta_js_1.generateMeta)(meta));
