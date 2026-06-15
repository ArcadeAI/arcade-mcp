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
// https://sonarsource.github.io/rspec/#/rspec/S2004/javascript
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
const location_js_1 = require("../helpers/location.js");
const test_frameworks_js_1 = require("../helpers/test-frameworks.js");
const meta = __importStar(require("./generated-meta.js"));
const DEFAULT_THRESHOLD = 4;
/**
 * Checks if a function is a callback argument to a test framework function.
 * For example: describe("test", () => { ... }) or it("should work", function() { ... })
 */
function isTestFrameworkCallback(node) {
    const { parent } = node;
    if (parent?.type !== 'CallExpression') {
        return false;
    }
    return (0, test_frameworks_js_1.isTestFrameworkCall)(parent);
}
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta),
    create(context) {
        const max = context.options[0]?.threshold ?? DEFAULT_THRESHOLD;
        const nestedStack = [];
        return {
            ':function'(node) {
                const fn = node;
                // Don't count test framework callbacks toward nesting depth
                if (isTestFrameworkCallback(fn)) {
                    return;
                }
                nestedStack.push(fn);
                if (nestedStack.length === max + 1) {
                    const secondaries = nestedStack.slice(0, -1);
                    (0, location_js_1.report)(context, {
                        loc: (0, location_js_1.getMainFunctionTokenLocation)(fn, fn.parent, context),
                        message: `Refactor this code to not nest functions more than ${max} levels deep.`,
                    }, secondaries.map(n => (0, location_js_1.toSecondaryLocation)({
                        loc: (0, location_js_1.getMainFunctionTokenLocation)(n, n.parent, context),
                    }, 'Nesting +1')));
                }
            },
            ':function:exit'(node) {
                // Only pop if we pushed (i.e., current node is on the stack)
                if (nestedStack.at(-1) === node) {
                    nestedStack.pop();
                }
            },
        };
    },
};
