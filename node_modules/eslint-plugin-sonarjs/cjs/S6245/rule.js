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
// https://sonarsource.github.io/rspec/#/rspec/S6245/javascript
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
const ENCRYPTED_KEY = 'encryption';
const messages = {
    unencrypted: 'Objects in the bucket are not encrypted. Make sure it is safe here.',
    omitted: 'Omitting "encryption" disables server-side encryption. Make sure it is safe here.',
};
exports.rule = (0, s3_js_1.S3BucketTemplate)((bucket, context) => {
    const encryptedProperty = (0, s3_js_1.getBucketProperty)(context, bucket, ENCRYPTED_KEY);
    if (encryptedProperty == null) {
        (0, location_js_1.report)(context, {
            message: messages['omitted'],
            node: bucket.callee,
        });
        return;
    }
    const encryptedValue = (0, ast_js_1.getValueOfExpression)(context, encryptedProperty.value, 'MemberExpression');
    if (encryptedValue && isUnencrypted(encryptedValue)) {
        const propagated = (0, s3_js_1.findPropagatedSetting)(encryptedProperty, encryptedValue);
        (0, location_js_1.report)(context, {
            message: messages['unencrypted'],
            node: encryptedProperty,
        }, propagated ? [propagated] : []);
    }
    function isUnencrypted(encrypted) {
        return ((0, cdk_js_1.normalizeFQN)((0, module_js_1.getFullyQualifiedName)(context, encrypted)) ===
            'aws_cdk_lib.aws_s3.BucketEncryption.UNENCRYPTED');
    }
}, (0, generate_meta_js_1.generateMeta)(meta));
