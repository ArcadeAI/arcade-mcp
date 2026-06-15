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
// https://sonarsource.github.io/rspec/#/rspec/S5734/javascript
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
const express_js_1 = require("../helpers/express.js");
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const module_js_1 = require("../helpers/module.js");
const ast_js_1 = require("../helpers/ast.js");
const meta = __importStar(require("./generated-meta.js"));
const HSTS = 'hsts';
const HELMET = 'helmet';
const MAX_AGE = 'maxAge';
const INCLUDE_SUB_DOMAINS = 'includeSubDomains';
const RECOMMENDED_MAX_AGE = 15552000;
exports.rule = (0, express_js_1.SensitiveMiddlewarePropertyRule)(findSensitiveTransportSecurityPolicyProperty, `Disabling Strict-Transport-Security policy is security-sensitive.`, (0, generate_meta_js_1.generateMeta)(meta));
function findSensitiveTransportSecurityPolicyProperty(context, node) {
    const sensitiveFinders = [findSensitiveHsts, findSensitiveMaxAge, findSensitiveIncludeSubDomains];
    const sensitives = [];
    const { callee, arguments: args } = node;
    if (args.length === 1 && args[0].type === 'ObjectExpression') {
        const [options] = args;
        for (const finder of sensitiveFinders) {
            const maybeSensitive = finder(context, callee, options);
            if (maybeSensitive) {
                sensitives.push(maybeSensitive);
            }
        }
    }
    return sensitives;
}
function findSensitiveHsts(context, middleware, options) {
    if ((0, module_js_1.getFullyQualifiedName)(context, middleware) === HELMET) {
        return (0, ast_js_1.getPropertyWithValue)(context, options, HSTS, false);
    }
    return undefined;
}
function findSensitiveMaxAge(context, middleware, options) {
    if (isHstsMiddlewareNode(context, middleware)) {
        const maybeMaxAgeProperty = (0, ast_js_1.getProperty)(options, MAX_AGE, context);
        if (maybeMaxAgeProperty) {
            const maybeMaxAgeValue = (0, ast_js_1.getValueOfExpression)(context, maybeMaxAgeProperty.value, 'Literal');
            if (typeof maybeMaxAgeValue?.value === 'number' &&
                maybeMaxAgeValue.value < RECOMMENDED_MAX_AGE) {
                return maybeMaxAgeProperty;
            }
        }
    }
    return undefined;
}
function findSensitiveIncludeSubDomains(context, middleware, options) {
    if (isHstsMiddlewareNode(context, middleware)) {
        return (0, ast_js_1.getPropertyWithValue)(context, options, INCLUDE_SUB_DOMAINS, false);
    }
    return undefined;
}
function isHstsMiddlewareNode(context, node) {
    const fqn = (0, module_js_1.getFullyQualifiedName)(context, node);
    return fqn === `${HELMET}.${HSTS}` || fqn === HSTS;
}
