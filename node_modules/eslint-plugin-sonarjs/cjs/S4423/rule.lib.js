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
const module_js_1 = require("../helpers/module.js");
const ast_js_1 = require("../helpers/ast.js");
const SECURE_PROTOCOL_ALLOWED_VALUES = new Set([
    'TLSv1_2_method',
    'TLSv1_2_client_method',
    'TLSv1_2_server_method',
    'TLS_method',
    'TLS_client_method',
    'TLS_server_method',
]);
exports.rule = {
    meta: {
        messages: {
            useMinimumTLS: "Change '{{option}}' to use at least TLS v1.2.",
            useSecureTLS: "Change '{{option}}' to allow only secure TLS versions.",
            AWSApiGateway: 'Change this code to enforce TLS 1.2 or above.',
            AWSOpenElasticSearch: 'Omitting "tlsSecurityPolicy" enables a deprecated version of TLS. Set it to enforce TLS 1.2 or above.',
        },
    },
    create(context) {
        function getValueOfProperty(objectExpression, propertyName) {
            const unsafeProperty = objectExpression && (0, ast_js_1.getProperty)(objectExpression, propertyName, context);
            if (unsafeProperty) {
                return (0, ast_js_1.getValueOfExpression)(context, unsafeProperty.value, 'Literal');
            }
            return undefined;
        }
        function checkMinMaxVersion(propertyName, property) {
            if (property && (property.value === 'TLSv1.1' || property.value === 'TLSv1')) {
                context.report({
                    node: property,
                    messageId: 'useMinimumTLS',
                    data: {
                        option: propertyName,
                    },
                });
            }
        }
        function checkSslOptions(optionsNode) {
            const options = (0, ast_js_1.getValueOfExpression)(context, optionsNode, 'ObjectExpression');
            const minVersion = getValueOfProperty(options, 'minVersion');
            const maxVersion = getValueOfProperty(options, 'maxVersion');
            checkMinMaxVersion('minVersion', minVersion);
            checkMinMaxVersion('maxVersion', maxVersion);
            const secureProtocol = getValueOfProperty(options, 'secureProtocol');
            const secureProtocolValue = secureProtocol?.value?.toString() ?? '';
            if (secureProtocol && !SECURE_PROTOCOL_ALLOWED_VALUES.has(secureProtocolValue)) {
                context.report({
                    node: secureProtocol,
                    messageId: 'useMinimumTLS',
                    data: {
                        option: 'secureProtocol',
                    },
                });
            }
            const secureOptions = (0, ast_js_1.getProperty)(options, 'secureOptions', context);
            if (secureOptions && !isValidSecureOptions(secureOptions.value)) {
                context.report({
                    node: secureOptions,
                    messageId: 'useSecureTLS',
                    data: {
                        option: 'secureOptions',
                    },
                });
            }
        }
        function isValidSecureOptions(options) {
            const flags = [];
            collectIdentifiersFromBinary(options, flags);
            return (flags[0] === null ||
                (flags.includes('SSL_OP_NO_TLSv1') && flags.includes('SSL_OP_NO_TLSv1_1')));
        }
        function collectIdentifiersFromBinary(node, acc) {
            if (node.type === 'BinaryExpression') {
                collectIdentifiersFromBinary(node.left, acc);
                collectIdentifiersFromBinary(node.right, acc);
            }
            else if (node.type === 'MemberExpression' &&
                (0, module_js_1.getFullyQualifiedName)(context, node.object) === 'constants' &&
                node.property.type === 'Identifier') {
                acc.push(node.property.name);
            }
            else {
                // if part of expression is some complex node like function call, we set null on index 0
                acc[0] = null;
            }
        }
        return {
            CallExpression: (node) => {
                const callExpression = node;
                const fqn = (0, module_js_1.getFullyQualifiedName)(context, callExpression);
                // https://nodejs.org/api/https.html#https_https_get_options_callback
                if (fqn === 'https.request') {
                    checkSslOptions(callExpression.arguments[0]);
                    checkSslOptions(callExpression.arguments[1]);
                }
                // https://github.com/request/request#tlsssl-protocol
                if (fqn === 'request.get') {
                    checkSslOptions(callExpression.arguments[0]);
                }
                // https://nodejs.org/api/tls.html#tls_tls_connect_options_callback
                if (fqn === 'tls.connect') {
                    checkSslOptions(callExpression.arguments[0]);
                    checkSslOptions(callExpression.arguments[1]);
                    checkSslOptions(callExpression.arguments[2]);
                }
                // https://nodejs.org/api/tls.html#tls_tls_createsecurecontext_options
                if (fqn === 'tls.createSecureContext') {
                    checkSslOptions(callExpression.arguments[0]);
                }
            },
        };
    },
};
