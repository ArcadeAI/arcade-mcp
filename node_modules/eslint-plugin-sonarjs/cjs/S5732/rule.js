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
// https://sonarsource.github.io/rspec/#/rspec/S5732/javascript
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
const HELMET = 'helmet';
const HELMET_CSP = 'helmet-csp';
const DIRECTIVES = 'directives';
const NONE = "'none'";
const CONTENT_SECURITY_POLICY = 'contentSecurityPolicy';
const FRAME_ANCESTORS_CAMEL = 'frameAncestors';
const FRAME_ANCESTORS_HYPHEN = 'frame-ancestors';
exports.rule = (0, express_js_1.SensitiveMiddlewarePropertyRule)(findDirectivesWithSensitiveFrameAncestorsPropertyFromHelmet, `Make sure disabling content security policy frame-ancestors directive is safe here.`, (0, generate_meta_js_1.generateMeta)(meta));
function findDirectivesWithSensitiveFrameAncestorsPropertyFromHelmet(context, node) {
    const { arguments: args } = node;
    if (isValidHelmetModuleCall(context, node) && args.length === 1) {
        const [options] = args;
        const maybeDirectives = (0, ast_js_1.getProperty)(options, DIRECTIVES, context);
        if (maybeDirectives) {
            const maybeFrameAncestors = getFrameAncestorsProperty(maybeDirectives, context);
            if (!maybeFrameAncestors) {
                return [maybeDirectives];
            }
            if (isSetNoneFrameAncestorsProperty(maybeFrameAncestors)) {
                return [maybeFrameAncestors];
            }
        }
    }
    return [];
}
function isValidHelmetModuleCall(context, callExpr) {
    /* csp(options) or helmet.contentSecurityPolicy(options) */
    const fqn = (0, module_js_1.getFullyQualifiedName)(context, callExpr);
    return fqn === HELMET_CSP || fqn === `${HELMET}.${CONTENT_SECURITY_POLICY}`;
}
function isSetNoneFrameAncestorsProperty(frameAncestors) {
    const { value } = frameAncestors;
    return (value.type === 'ArrayExpression' &&
        Boolean(value.elements.some(v => v?.type === 'Literal' && typeof v.value === 'string' && v.value === NONE)));
}
function getFrameAncestorsProperty(directives, context) {
    const propertyKeys = [FRAME_ANCESTORS_CAMEL, FRAME_ANCESTORS_HYPHEN];
    for (const propertyKey of propertyKeys) {
        const maybeProperty = (0, ast_js_1.getProperty)(directives.value, propertyKey, context);
        if (maybeProperty) {
            return maybeProperty;
        }
    }
    return undefined;
}
