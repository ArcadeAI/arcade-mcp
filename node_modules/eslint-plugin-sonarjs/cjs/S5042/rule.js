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
// https://sonarsource.github.io/rspec/#/rspec/S5042/javascript
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
const ast_js_1 = require("../helpers/ast.js");
const meta = __importStar(require("./generated-meta.js"));
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            safeExpanding: 'Make sure that expanding this archive file is safe here.',
        },
    }),
    create(context) {
        function isSensitiveTarCall(call, fqn) {
            if (fqn === 'tar.x') {
                const firstArg = call.arguments.length > 0 ? call.arguments[0] : null;
                if (!firstArg) {
                    return false;
                }
                const firstArgValue = (0, ast_js_1.getValueOfExpression)(context, firstArg, 'ObjectExpression');
                return (!!firstArgValue && !firstArgValue.properties.some(prop => canBeProperty(prop, 'filter')));
            }
            return false;
        }
        function isSensitiveExtractZipCall(call, fqn) {
            if (fqn === 'extract-zip') {
                const secondArg = call.arguments.length > 1 ? call.arguments[1] : null;
                if (!secondArg) {
                    return false;
                }
                const secondArgValue = (0, ast_js_1.getValueOfExpression)(context, secondArg, 'ObjectExpression');
                return (!!secondArgValue &&
                    !secondArgValue.properties.some(prop => canBeProperty(prop, 'onEntry')));
            }
            return false;
        }
        return {
            CallExpression(node) {
                const call = node;
                const fqn = (0, module_js_1.getFullyQualifiedName)(context, call);
                if (isSensitiveTarCall(call, fqn) ||
                    isSensitiveExtractZipCall(call, fqn) ||
                    fqn === 'jszip.loadAsync' ||
                    fqn === 'yauzl.open' ||
                    fqn === 'adm-zip.extractAllTo') {
                    context.report({
                        messageId: 'safeExpanding',
                        node: call.callee,
                    });
                }
            },
        };
    },
};
function canBeProperty(prop, name) {
    return (prop.type === 'SpreadElement' ||
        (0, ast_js_1.isIdentifier)(prop.key, name) ||
        ((0, ast_js_1.isLiteral)(prop.key) && prop.key.value === name));
}
