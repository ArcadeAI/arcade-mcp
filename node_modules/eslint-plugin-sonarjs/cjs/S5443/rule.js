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
// https://sonarsource.github.io/rspec/#/rspec/S5443/javascript
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
const meta = __importStar(require("./generated-meta.js"));
const UNIX_DIRECTORIES = [
    '/tmp/',
    '/var/tmp/',
    '/usr/tmp/',
    '/dev/shm/',
    '/dev/mqueue/',
    '/run/lock/',
    '/var/run/lock/',
    '/library/caches/',
    '/users/shared/',
    '/private/tmp/',
    '/private/var/tmp/',
].map(v => new RegExp(`^${v}`, 'i'));
const WINDOWS_DIRECTORIES_PATTERN = new RegExp(String.raw `^[^\\]*(\\){1,2}(Windows(\\){1,2}Temp|Temp|TMP)(\\.*|$)`, 'i');
const SENSITIVE_ENV_VARIABLES = new Set(['TMPDIR', 'TMP', 'TEMPDIR', 'TEMP']);
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            safeDirectory: 'Make sure publicly writable directories are used safely here.',
        },
    }),
    create(context) {
        return {
            Literal: (node) => {
                const literal = node;
                // Using literal.raw instead of literal.value as the latter escapes backslashes
                const value = literal.raw?.slice(1, -1);
                if (value &&
                    (UNIX_DIRECTORIES.some(i => value.match(i)) || WINDOWS_DIRECTORIES_PATTERN.test(value))) {
                    context.report({
                        node: literal,
                        messageId: 'safeDirectory',
                    });
                }
            },
            MemberExpression: (node) => {
                const memberExpression = node;
                const { object, property } = memberExpression;
                if (property.type !== 'Identifier' ||
                    !SENSITIVE_ENV_VARIABLES.has(property.name) ||
                    object.type !== 'MemberExpression') {
                    return;
                }
                if (object.property.type === 'Identifier' &&
                    object.property.name === 'env' &&
                    object.object.type === 'Identifier' &&
                    object.object.name === 'process') {
                    context.report({ node: memberExpression, messageId: 'safeDirectory' });
                }
            },
        };
    },
};
