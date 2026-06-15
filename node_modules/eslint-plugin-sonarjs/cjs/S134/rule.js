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
// https://sonarsource.github.io/rspec/#/rspec/S134/javascript
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
const collection_js_1 = require("../helpers/collection.js");
const location_js_1 = require("../helpers/location.js");
const meta = __importStar(require("./generated-meta.js"));
const DEFAULT_MAXIMUM_NESTING_LEVEL = 3;
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta),
    create(context) {
        const sourceCode = context.sourceCode;
        const threshold = context.options[0]?.maximumNestingLevel ??
            DEFAULT_MAXIMUM_NESTING_LEVEL;
        const nodeStack = [];
        function push(n) {
            nodeStack.push(n);
        }
        function pop() {
            return nodeStack.pop();
        }
        function check(node) {
            if (nodeStack.length === threshold) {
                (0, location_js_1.report)(context, {
                    message: `Refactor this code to not nest more than ${threshold} if/for/while/switch/try statements.`,
                    loc: sourceCode.getFirstToken(node).loc,
                }, nodeStack.map(n => (0, location_js_1.toSecondaryLocation)(n, '+1')));
            }
        }
        function isElseIf(node) {
            const parent = (0, collection_js_1.last)(context.sourceCode.getAncestors(node));
            return (node.type === 'IfStatement' && parent.type === 'IfStatement' && node === parent.alternate);
        }
        const controlFlowNodes = [
            'ForStatement',
            'ForInStatement',
            'ForOfStatement',
            'WhileStatement',
            'DoWhileStatement',
            'IfStatement',
            'TryStatement',
            'SwitchStatement',
        ].join(',');
        return {
            [controlFlowNodes]: (node) => {
                if (isElseIf(node)) {
                    pop();
                    push(sourceCode.getFirstToken(node));
                }
                else {
                    check(node);
                    push(sourceCode.getFirstToken(node));
                }
            },
            [`${controlFlowNodes}:exit`]: (node) => {
                if (!isElseIf(node)) {
                    pop();
                }
            },
        };
    },
};
