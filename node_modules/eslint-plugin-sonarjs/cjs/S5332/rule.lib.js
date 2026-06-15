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
const node_url_1 = require("node:url");
const module_js_1 = require("../helpers/module.js");
const ancestor_js_1 = require("../helpers/ancestor.js");
const ast_js_1 = require("../helpers/ast.js");
const cdk_js_1 = require("../helpers/aws/cdk.js");
const INSECURE_PROTOCOLS = ['http://', 'ftp://', 'telnet://'];
const LOOPBACK_PATTERN = /localhost|127(?:\.\d+){0,2}\.\d+$|\/\/(?:0*:)*?:?0*1$/;
const EXCEPTION_FULL_HOSTS = new Set([
    'www.w3.org',
    'xml.apache.org',
    'schemas.xmlsoap.org',
    'schemas.openxmlformats.org',
    'rdfs.org',
    'purl.org',
    'xmlns.com',
    'schemas.google.com',
    'a9.com',
    'ns.adobe.com',
    'ltsc.ieee.org',
    'docbook.org',
    'graphml.graphdrawing.org',
    'json-schema.org',
    'schemas.microsoft.com',
]);
const EXCEPTION_TOP_HOSTS = [
    /\.example$/,
    /\.?example\.com$/,
    /\.?example\.org$/,
    /\.test$/,
    /\.?test\.com$/,
];
exports.rule = {
    meta: {
        messages: {
            insecureProtocol: 'Using {{protocol}} protocol is insecure. Use {{alternative}} instead.',
        },
    },
    create(context) {
        function checkNodemailer(callExpression) {
            const firstArg = callExpression.arguments.length > 0 ? callExpression.arguments[0] : null;
            if (!firstArg) {
                return;
            }
            const firstArgValue = (0, ast_js_1.getValueOfExpression)(context, firstArg, 'ObjectExpression');
            const ses = (0, ast_js_1.getProperty)(firstArgValue, 'SES', context);
            if (ses && usesSesCommunication(ses)) {
                return;
            }
            const secure = (0, ast_js_1.getProperty)(firstArgValue, 'secure', context);
            if (secure && (secure.value.type !== 'Literal' || secure.value.raw !== 'false')) {
                return;
            }
            const requireTls = (0, ast_js_1.getProperty)(firstArgValue, 'requireTLS', context);
            if (requireTls && (requireTls.value.type !== 'Literal' || requireTls.value.raw !== 'false')) {
                return;
            }
            const port = (0, ast_js_1.getProperty)(firstArgValue, 'port', context);
            if (port && (port.value.type !== 'Literal' || port.value.raw === '465')) {
                return;
            }
            context.report({ node: callExpression.callee, ...getMessageAndData('http') });
        }
        function usesSesCommunication(sesProperty) {
            const configuration = (0, ast_js_1.getValueOfExpression)(context, sesProperty.value, 'ObjectExpression');
            if (!configuration) {
                return false;
            }
            const ses = (0, ast_js_1.getValueOfExpression)(context, (0, ast_js_1.getProperty)(configuration, 'ses', context)?.value, 'NewExpression');
            if (!ses || (0, cdk_js_1.normalizeFQN)((0, module_js_1.getFullyQualifiedName)(context, ses)) !== '@aws_sdk.client_ses.SES') {
                return false;
            }
            const aws = (0, ast_js_1.getProperty)(configuration, 'aws', context);
            if (!aws ||
                (0, cdk_js_1.normalizeFQN)((0, module_js_1.getFullyQualifiedName)(context, aws.value)) !== '@aws_sdk.client_ses') {
                return false;
            }
            return true;
        }
        function checkCallToFtp(callExpression) {
            if (callExpression.callee.type === 'MemberExpression' &&
                callExpression.callee.property.type === 'Identifier' &&
                callExpression.callee.property.name === 'connect') {
                const newExpression = (0, ast_js_1.getValueOfExpression)(context, callExpression.callee.object, 'NewExpression');
                if (!!newExpression && (0, module_js_1.getFullyQualifiedName)(context, newExpression.callee) === 'ftp') {
                    const firstArg = callExpression.arguments.length > 0 ? callExpression.arguments[0] : null;
                    if (!firstArg) {
                        return;
                    }
                    const firstArgValue = (0, ast_js_1.getValueOfExpression)(context, firstArg, 'ObjectExpression');
                    const secure = (0, ast_js_1.getProperty)(firstArgValue, 'secure', context);
                    if (secure?.value.type === 'Literal' && secure.value.raw === 'false') {
                        context.report({
                            node: callExpression.callee,
                            ...getMessageAndData('ftp'),
                        });
                    }
                }
            }
        }
        function checkCallToRequire(callExpression) {
            if (callExpression.callee.type === 'Identifier' && callExpression.callee.name === 'require') {
                const firstArg = callExpression.arguments.length > 0 ? callExpression.arguments[0] : null;
                if (firstArg?.type === 'Literal' &&
                    typeof firstArg.value === 'string' &&
                    firstArg.value === 'telnet-client') {
                    context.report({
                        node: firstArg,
                        ...getMessageAndData('telnet'),
                    });
                }
            }
        }
        function isExceptionUrl(value, node) {
            if (INSECURE_PROTOCOLS.includes(value)) {
                const parent = (0, ancestor_js_1.getParent)(context, node);
                return !(parent?.type === 'BinaryExpression' && parent.operator === '+');
            }
            return hasExceptionHost(value);
        }
        return {
            Literal: (node) => {
                const literal = node;
                if (typeof literal.value === 'string') {
                    const value = literal.value.trim().toLocaleLowerCase();
                    const insecure = INSECURE_PROTOCOLS.find(protocol => value.startsWith(protocol));
                    if (insecure && !isExceptionUrl(value, node)) {
                        const protocol = insecure.substring(0, insecure.indexOf(':'));
                        context.report({
                            ...getMessageAndData(protocol),
                            node,
                        });
                    }
                }
            },
            CallExpression: (node) => {
                const callExpression = node;
                if ((0, module_js_1.getFullyQualifiedName)(context, callExpression) === 'nodemailer.createTransport') {
                    checkNodemailer(callExpression);
                }
                checkCallToFtp(callExpression);
                checkCallToRequire(callExpression);
            },
            ImportDeclaration: (node) => {
                const importDeclaration = node;
                if (typeof importDeclaration.source.value === 'string' &&
                    importDeclaration.source.value === 'telnet-client') {
                    context.report({
                        node: importDeclaration.source,
                        ...getMessageAndData('telnet'),
                    });
                }
            },
        };
    },
};
function getMessageAndData(protocol) {
    let alternative;
    switch (protocol) {
        case 'http':
            alternative = 'https';
            break;
        case 'ftp':
            alternative = 'sftp, scp or ftps';
            break;
        default:
            alternative = 'ssh';
    }
    return { messageId: 'insecureProtocol', data: { protocol, alternative } };
}
function hasExceptionHost(value) {
    let url;
    try {
        url = new node_url_1.URL(value);
    }
    catch {
        return false;
    }
    const host = url.hostname;
    return (host.length === 0 ||
        LOOPBACK_PATTERN.test(host) ||
        EXCEPTION_FULL_HOSTS.has(host) ||
        EXCEPTION_TOP_HOSTS.some(exception => exception.test(host)));
}
