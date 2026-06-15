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
// https://sonarsource.github.io/rspec/#/rspec/S2187/javascript
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
const APIs = new Set([
    // Jasmine
    'it',
    'fit',
    'xit',
    // Jest
    'it',
    'it.concurrent',
    'it.concurrent.each',
    'it.concurrent.only.each',
    'it.concurrent.skip.each',
    'it.each',
    'it.failing',
    'it.failing.each',
    'it.only.failing',
    'it.skip.failing',
    'it.only',
    'it.only.each',
    'it.skip',
    'it.skip.each',
    'it.todo',
    'test',
    'test.concurrent',
    'test.concurrent.each',
    'test.concurrent.only.each',
    'test.concurrent.skip.each',
    'test.each',
    'test.failing',
    'test.failing.each',
    'test.only.failing',
    'test.skip.failing',
    'test.only',
    'test.only.each',
    'test.skip',
    'test.skip.each',
    'test.todo',
    // Mocha
    'it',
    'it.skip',
    'it.only',
    'test',
    'test.skip',
    'test.only',
    // Node.js
    'it',
    'it.skip',
    'it.todo',
    'it.only',
    'test',
    'test.skip',
    'test.todo',
    'test.only',
    // vitest
    'test.runIf',
    'it.runIf',
    'test.for',
    'it.for',
    // eslint rule tester
    'ruleTester.run',
]);
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            missingTest: 'Add some tests to this file or delete it.',
        },
    }),
    create(context) {
        const { filename } = context;
        if (!/\.spec\.|\.test\./.test(filename)) {
            return {};
        }
        let hasTest = false;
        function checkIfTestCall(node) {
            if (hasTest) {
                return;
            }
            const fqn = fullyQualifiedName(node);
            if (APIs.has(fqn)) {
                hasTest = true;
            }
        }
        return {
            CallExpression(node) {
                checkIfTestCall(node.callee);
            },
            TaggedTemplateExpression(node) {
                checkIfTestCall(node.tag);
            },
            'Program:exit'() {
                if (!hasTest) {
                    context.report({
                        messageId: 'missingTest',
                        loc: { line: 0, column: 0 },
                    });
                }
            },
        };
    },
};
function fullyQualifiedName(node) {
    switch (node.type) {
        case 'Identifier':
            return node.name;
        case 'MemberExpression':
            return `${fullyQualifiedName(node.object)}.${fullyQualifiedName(node.property)}`;
        default:
            return '';
    }
}
