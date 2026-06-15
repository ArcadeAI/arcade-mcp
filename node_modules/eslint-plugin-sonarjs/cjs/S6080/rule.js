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
// https://sonarsource.github.io/rspec/#/rspec/S6080/javascript
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
const chai_js_1 = require("../helpers/chai.js");
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const ast_js_1 = require("../helpers/ast.js");
const mocha_js_1 = require("../helpers/mocha.js");
const meta = __importStar(require("./generated-meta.js"));
const MESSAGE = 'Set this timeout to 0 if you want to disable it, otherwise use a value lower than 2147483648.';
const MAX_DELAY_VALUE = 2_147_483_647;
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta),
    create(context) {
        if (!(0, chai_js_1.isImported)(context)) {
            return {};
        }
        const constructs = [];
        return {
            CallExpression: (node) => {
                if ((0, mocha_js_1.isTestConstruct)(node)) {
                    constructs.push(node);
                    return;
                }
                if (constructs.length > 0) {
                    checkTimeoutDisabling(node, context);
                }
            },
            'CallExpression:exit': (node) => {
                if ((0, mocha_js_1.isTestConstruct)(node)) {
                    constructs.pop();
                }
            },
        };
    },
};
function checkTimeoutDisabling(node, context) {
    if ((0, ast_js_1.isMethodCall)(node) && node.arguments.length > 0) {
        const { callee: { object, property }, arguments: [value], } = node;
        if ((0, ast_js_1.isThisExpression)(object) &&
            (0, ast_js_1.isIdentifier)(property, 'timeout') &&
            isDisablingTimeout(value, context)) {
            context.report({
                message: MESSAGE,
                node: value,
            });
        }
    }
}
function isDisablingTimeout(timeout, context) {
    const usage = (0, ast_js_1.getUniqueWriteUsageOrNode)(context, timeout);
    return (0, ast_js_1.isNumberLiteral)(usage) && usage.value > MAX_DELAY_VALUE;
}
