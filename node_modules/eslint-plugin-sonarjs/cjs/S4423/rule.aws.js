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
// https://sonarsource.github.io/rspec/#/rspec/S4423/javascript
Object.defineProperty(exports, "__esModule", { value: true });
exports.rule = void 0;
const cdk_js_1 = require("../helpers/aws/cdk.js");
exports.rule = (0, cdk_js_1.AwsCdkTemplate)({
    'aws_cdk_lib.aws_apigateway.CfnDomainName': (0, cdk_js_1.AwsCdkCheckArguments)('AWSApiGateway', true, 'securityPolicy', { primitives: { valid: ['TLS_1_2'] } }),
    'aws_cdk_lib.aws_apigateway.DomainName': (0, cdk_js_1.AwsCdkCheckArguments)('AWSApiGateway', false, 'securityPolicy', { fqns: { valid: ['aws_cdk_lib.aws_apigateway.SecurityPolicy.TLS_1_2'] } }),
    'aws_cdk_lib.aws_elasticsearch.CfnDomain': (0, cdk_js_1.AwsCdkCheckArguments)(['AWSOpenElasticSearch', 'enforceTLS12'], true, ['domainEndpointOptions', 'tlsSecurityPolicy'], {
        primitives: { valid: ['Policy-Min-TLS-1-2-2019-07', 'Policy-Min-TLS-1-2-PFS-2023-10'] },
    }),
    'aws_cdk_lib.aws_opensearchservice.Domain': (0, cdk_js_1.AwsCdkCheckArguments)(['AWSOpenElasticSearch', 'enforceTLS12'], true, 'tlsSecurityPolicy', {
        fqns: {
            valid: [
                'aws_cdk_lib.aws_opensearchservice.TLSSecurityPolicy.TLS_1_2',
                'aws_cdk_lib.aws_opensearchservice.TLSSecurityPolicy.TLS_1_2_PFS',
            ],
        },
    }),
    'aws_cdk_lib.aws_opensearchservice.CfnDomain': (0, cdk_js_1.AwsCdkCheckArguments)(['AWSOpenElasticSearch', 'enforceTLS12'], true, ['domainEndpointOptions', 'tlsSecurityPolicy'], {
        primitives: { valid: ['Policy-Min-TLS-1-2-2019-07', 'Policy-Min-TLS-1-2-PFS-2023-10'] },
    }),
    'aws_cdk_lib.aws_elasticsearch.Domain': (0, cdk_js_1.AwsCdkCheckArguments)(['AWSOpenElasticSearch', 'enforceTLS12'], true, 'tlsSecurityPolicy', {
        fqns: {
            valid: [
                'aws_cdk_lib.aws_elasticsearch.TLSSecurityPolicy.TLS_1_2',
                'aws_cdk_lib.aws_elasticsearch.TLSSecurityPolicy.TLS_1_2_PFS',
            ],
        },
    }),
}, {
    messages: {
        enforceTLS12: 'Change this code to enforce TLS 1.2 or above.',
        AWSApiGateway: 'Change this code to enforce TLS 1.2 or above.',
        AWSOpenElasticSearch: 'Omitting "tlsSecurityPolicy" enables a deprecated version of TLS. Set it to enforce TLS 1.2 or above.',
    },
});
