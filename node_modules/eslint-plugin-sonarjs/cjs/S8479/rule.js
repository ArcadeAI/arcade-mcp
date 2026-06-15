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
// https://sonarsource.github.io/rspec/#/rspec/S8479/javascript
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
const module_ts_js_1 = require("../helpers/module-ts.js");
const parser_services_js_1 = require("../helpers/parser-services.js");
const meta = __importStar(require("./generated-meta.js"));
const DANGEROUS_TAGS = new Set([
    'script',
    'iframe',
    'object',
    'embed',
    'form',
    'input',
    'textarea',
    'select',
    'meta',
    'link',
    'style',
    'base',
    'svg',
    'math',
]);
const EVENT_HANDLER_PATTERN = /^on[a-z]/i;
/**
 * URI-carrying attributes that must never be added to ADD_URI_SAFE_ATTR.
 * Marking them as "URI-safe" skips DOMPurify's javascript: URI check,
 * enabling 1-click XSS via crafted href/src/action values.
 */
const DANGEROUS_URI_ATTRS = new Set(['href', 'src', 'action', 'formaction', 'xlink:href', 'data']);
/**
 * Boolean options that are dangerous when set to the specified value.
 */
const DANGEROUS_BOOLEAN_OPTIONS = {
    ALLOW_UNKNOWN_PROTOCOLS: true,
    WHOLE_DOCUMENT: true,
    SAFE_FOR_XML: false,
    SANITIZE_DOM: false,
    RETURN_TRUSTED_TYPE: false,
};
const MAX_ACTIONS_IN_MESSAGE = 2;
const SANITIZE_FQNS = new Set(['dompurify.sanitize', 'isomorphic-dompurify.sanitize']);
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            unsafeConfig: 'unsafeConfig',
        },
    }),
    create(context) {
        const services = context.sourceCode.parserServices;
        const hasTypeInformation = (0, parser_services_js_1.isRequiredParserServices)(services);
        return {
            CallExpression(node) {
                let fqn = null;
                if (hasTypeInformation) {
                    const tsNode = services.esTreeNodeToTSNodeMap.get(node);
                    fqn = (0, module_ts_js_1.getFullyQualifiedNameTS)(services, tsNode);
                }
                else {
                    fqn = (0, module_js_1.getFullyQualifiedName)(context, node);
                }
                if (!fqn || !SANITIZE_FQNS.has(fqn)) {
                    return;
                }
                const configArg = node.arguments[1];
                if (configArg?.type !== 'ObjectExpression') {
                    return;
                }
                const actions = collectActions(configArg);
                if (actions.length > 0) {
                    context.report({
                        message: buildMessage(actions),
                        node: configArg,
                    });
                }
            },
        };
    },
};
function collectActions(config) {
    const actions = [];
    for (const prop of config.properties) {
        if (prop.type !== 'Property') {
            continue;
        }
        const action = getActionForProperty(prop);
        if (action) {
            actions.push(action);
        }
    }
    return actions;
}
function getActionForProperty(prop) {
    const key = getPropertyName(prop);
    if (!key) {
        return undefined;
    }
    switch (key) {
        case 'ADD_TAGS':
        case 'ALLOWED_TAGS': {
            const dangerous = getDangerousArrayElements(prop.value, DANGEROUS_TAGS);
            return dangerous.length > 0 ? `remove ${formatList(dangerous)} from '${key}'` : undefined;
        }
        case 'ADD_ATTR':
        case 'ALLOWED_ATTR': {
            const dangerous = getDangerousAttributes(prop.value);
            return dangerous.length > 0 ? `remove ${formatList(dangerous)} from '${key}'` : undefined;
        }
        case 'ADD_URI_SAFE_ATTR': {
            const dangerous = getDangerousArrayElements(prop.value, DANGEROUS_URI_ATTRS);
            return dangerous.length > 0 ? `remove ${formatList(dangerous)} from '${key}'` : undefined;
        }
        case 'ALLOWED_URI_REGEXP':
            return isUnanchoredRegex(prop.value)
                ? `anchor the 'ALLOWED_URI_REGEXP' pattern with '^' to prevent partial URI matches`
                : undefined;
        default:
            if (key in DANGEROUS_BOOLEAN_OPTIONS) {
                const dangerousValue = DANGEROUS_BOOLEAN_OPTIONS[key];
                return isBooleanLiteral(prop.value, dangerousValue)
                    ? `set '${key}' to '${!dangerousValue}'`
                    : undefined;
            }
            return undefined;
    }
}
function buildMessage(actions) {
    const shown = actions.slice(0, MAX_ACTIONS_IN_MESSAGE);
    const remaining = actions.length - shown.length;
    let message = `To prevent DOM-based attacks, ${joinActions(shown)}.`;
    if (remaining > 0) {
        message += ` Plus ${remaining} more ${remaining === 1 ? 'issue' : 'issues'}. Read 'How to fix it' for all details.`;
    }
    return message;
}
function joinActions(actions) {
    if (actions.length === 1) {
        return actions[0];
    }
    return `${actions.slice(0, -1).join(', ')}, and ${actions.at(-1)}`;
}
function getPropertyName(prop) {
    if (prop.key.type === 'Identifier') {
        return prop.key.name;
    }
    if (prop.key.type === 'Literal' && typeof prop.key.value === 'string') {
        return prop.key.value;
    }
    return undefined;
}
function getDangerousArrayElements(node, dangerousSet) {
    if (node.type !== 'ArrayExpression') {
        return [];
    }
    return node.elements
        .filter((el) => el !== null &&
        el.type === 'Literal' &&
        typeof el.value === 'string' &&
        dangerousSet.has(el.value.toLowerCase()))
        .map(el => el.value);
}
function getDangerousAttributes(node) {
    if (node.type !== 'ArrayExpression') {
        return [];
    }
    return node.elements
        .filter((el) => el !== null &&
        el.type === 'Literal' &&
        typeof el.value === 'string' &&
        EVENT_HANDLER_PATTERN.test(el.value))
        .map(el => el.value);
}
function formatList(items) {
    const quoted = items.map(item => `'${item}'`);
    if (quoted.length === 1) {
        return quoted[0];
    }
    return `${quoted.slice(0, -1).join(', ')} and ${quoted.at(-1)}`;
}
function isBooleanLiteral(node, value) {
    return node.type === 'Literal' && node.value === value;
}
function isUnanchoredRegex(node) {
    if (node.type === 'Literal' && 'regex' in node && node.regex) {
        return !node.regex.pattern.startsWith('^');
    }
    return false;
}
