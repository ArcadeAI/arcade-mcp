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
// https://sonarsource.github.io/rspec/#/rspec/S6418/javascript
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
const ast_js_1 = require("../helpers/ast.js");
const entropy_js_1 = require("../helpers/entropy.js");
const meta = __importStar(require("./generated-meta.js"));
const DEFAULT_SECRET_WORDS = 'api[_.-]?key,auth,credential,secret,token';
const DEFAULT_RANDOMNESS_SENSIBILITY = 5;
const POSTVALIDATION_PATTERN = /[a-zA-Z0-9_.+/~$-]([a-zA-Z0-9_.+/=~$-]|\\\\\\\\(?![ntr"])){14,1022}[a-zA-Z0-9_.+/=~$-]/;
function message(name) {
    return `"${name}" detected here, make sure this is not a hard-coded secret.`;
}
let randomnessSensibility;
let secretWordRegexps;
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta),
    create(context) {
        // get typed rule options with FromSchema helper
        const secretWords = context.options[0]?.['secretWords'] ??
            DEFAULT_SECRET_WORDS;
        secretWordRegexps = buildSecretWordRegexps(secretWords);
        randomnessSensibility =
            context.options[0]?.['randomnessSensibility'] ??
                DEFAULT_RANDOMNESS_SENSIBILITY;
        return {
            AssignmentExpression(node) {
                handleAssignmentExpression(context, node);
            },
            AssignmentPattern(node) {
                handleAssignmentPattern(context, node);
            },
            Property(node) {
                handlePropertyAndPropertyDefinition(context, node);
            },
            PropertyDefinition(node) {
                handlePropertyAndPropertyDefinition(context, node);
            },
            VariableDeclarator(node) {
                handleVariableDeclarator(context, node);
            },
        };
    },
};
function handleAssignmentExpression(context, node) {
    const keySuspect = findKeySuspect(node.left);
    const valueSuspect = findValueSuspect(extractDefaultOperatorIfNeeded(node));
    if (keySuspect && valueSuspect) {
        context.report({
            node: node.right,
            message: message(keySuspect),
        });
    }
    function extractDefaultOperatorIfNeeded(node) {
        const defaultOperators = ['??', '||'];
        if ((0, ast_js_1.isLogicalExpression)(node.right) &&
            defaultOperators.includes(node.right.operator)) {
            return node.right.right;
        }
        else {
            return node.right;
        }
    }
}
function handleAssignmentPattern(context, node) {
    const keySuspect = findKeySuspect(node.left);
    const valueSuspect = findValueSuspect(node.right);
    if (keySuspect && valueSuspect) {
        context.report({
            node: node.right,
            message: message(keySuspect),
        });
    }
}
function handlePropertyAndPropertyDefinition(context, node) {
    const keySuspect = findKeySuspect(node.key);
    const valueSuspect = findValueSuspect(node.value);
    if (keySuspect && valueSuspect) {
        context.report({
            node: node.value,
            message: message(keySuspect),
        });
    }
}
function handleVariableDeclarator(context, node) {
    const keySuspect = findKeySuspect(node.id);
    const valueSuspect = findValueSuspect(node.init);
    if (keySuspect && valueSuspect) {
        context.report({
            node: node.init,
            message: message(keySuspect),
        });
    }
}
function findKeySuspect(node) {
    if ((0, ast_js_1.isIdentifier)(node) && secretWordRegexps.some(pattern => pattern.test(node.name))) {
        return node.name;
    }
    else if ((0, ast_js_1.isStringLiteral)(node) &&
        secretWordRegexps.some(pattern => pattern.test(node.value))) {
        return node.value;
    }
    else if (node.type === 'MemberExpression') {
        return findKeySuspect(node.property);
    }
    else {
        return undefined;
    }
}
function findValueSuspect(node) {
    if (!node) {
        return undefined;
    }
    if ((0, ast_js_1.isStringLiteral)(node) &&
        valuePassesPostValidation(node.value) &&
        entropyShouldRaise(node.value)) {
        return node;
    }
    // Check ternary expressions (ConditionalExpression)
    if (node.type === 'ConditionalExpression') {
        return findValueSuspect(node.consequent) ?? findValueSuspect(node.alternate);
    }
    return undefined;
}
function valuePassesPostValidation(value) {
    return POSTVALIDATION_PATTERN.test(value);
}
function buildSecretWordRegexps(secretWords) {
    try {
        return secretWords.split(',').map(word => new RegExp(`(${word})`, 'i'));
    }
    catch (e) {
        console.error(`Invalid characters provided to rule S6418 'no-hardcoded-secrets' parameter "secretWords": "${secretWords}" falling back to default: "${DEFAULT_SECRET_WORDS}". Error: ${e}`);
        return buildSecretWordRegexps(DEFAULT_SECRET_WORDS);
    }
}
function entropyShouldRaise(value) {
    return (0, entropy_js_1.shannonEntropy)(value) > randomnessSensibility;
}
