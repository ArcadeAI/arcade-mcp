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
// https://sonarsource.github.io/rspec/#/rspec/S6308/javascript
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
const result_js_1 = require("../helpers/result.js");
const meta = __importStar(require("./generated-meta.js"));
const DOMAIN_PROPS_POSITION = 2;
const ENABLED_PROPERTY = 'enabled';
const OPEN_SEARCH = 'OpenSearch';
const ELASTIC_SEARCH = 'Elasticsearch';
exports.rule = (0, cdk_js_1.AwsCdkTemplate)({
    'aws-cdk-lib.aws-opensearchservice.Domain': domainChecker({
        encryptionProperty: 'encryptionAtRest',
        version: {
            valueType: 'EngineVersion',
            property: 'version',
            defaultValue: OPEN_SEARCH,
        },
    }),
    'aws-cdk-lib.aws-opensearchservice.CfnDomain': domainChecker({
        encryptionProperty: 'encryptionAtRestOptions',
        version: {
            valueType: 'string',
            property: 'engineVersion',
            defaultValue: OPEN_SEARCH,
        },
    }),
    'aws-cdk-lib.aws-elasticsearch.Domain': domainChecker({
        encryptionProperty: 'encryptionAtRest',
        version: {
            valueType: 'ElasticsearchVersion',
            property: 'version',
            defaultValue: ELASTIC_SEARCH,
        },
    }),
    'aws-cdk-lib.aws-elasticsearch.CfnDomain': domainChecker({
        encryptionProperty: 'encryptionAtRestOptions',
        version: {
            valueType: 'string',
            property: 'elasticsearchVersion',
            defaultValue: ELASTIC_SEARCH,
        },
    }),
}, (0, generate_meta_js_1.generateMeta)(meta, {
    messages: {
        encryptionDisabled: 'Make sure that using unencrypted {{search}} domains is safe here.',
        encryptionOmitted: 'Omitting {{encryptionPropertyName}} causes encryption of data at rest to be ' +
            'disabled for this {{search}} domain. Make sure it is safe here.',
    },
}));
function domainChecker(options) {
    return (expr, ctx) => {
        const call = (0, result_js_1.getResultOfExpression)(ctx, expr);
        const argument = call.getArgument(DOMAIN_PROPS_POSITION);
        const encryption = argument.getProperty(options.encryptionProperty);
        const version = argument.getProperty(options.version.property);
        const isEnabled = encryption.getProperty(ENABLED_PROPERTY);
        const search = version.map(getSearchEngine) ?? options.version.defaultValue;
        if (isEnabled.isMissing) {
            ctx.report({
                messageId: 'encryptionOmitted',
                node: isEnabled.node,
                data: {
                    encryptionPropertyName: options.encryptionProperty,
                    search,
                },
            });
        }
        else if (isEnabled.isFound && isUnencrypted(isEnabled.node)) {
            ctx.report({
                messageId: 'encryptionDisabled',
                node: isEnabled.node,
                data: {
                    search,
                },
            });
        }
        function getSearchEngine(node) {
            let version;
            if (options.version.valueType === 'string' && (0, ast_js_1.isStringLiteral)(node)) {
                version = `${options.version.property}.${node.value}`;
            }
            else {
                version = (0, module_js_1.getFullyQualifiedName)(ctx, node);
            }
            for (const name of version?.toLowerCase().split('.').reverse() ?? []) {
                if (name.includes('opensearch')) {
                    return OPEN_SEARCH;
                }
                else if (name.includes('elasticsearch')) {
                    return ELASTIC_SEARCH;
                }
            }
            return null;
        }
    };
}
function isUnencrypted(node) {
    return (0, ast_js_1.isBooleanLiteral)(node) && !node.value;
}
