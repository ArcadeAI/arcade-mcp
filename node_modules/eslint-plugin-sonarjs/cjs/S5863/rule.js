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
// https://sonarsource.github.io/rspec/#/rspec/S5863/javascript
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
const equivalence_js_1 = require("../helpers/equivalence.js");
const chai_js_1 = require("../helpers/chai.js");
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const ast_js_1 = require("../helpers/ast.js");
const location_js_1 = require("../helpers/location.js");
const meta = __importStar(require("./generated-meta.js"));
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta),
    create(context) {
        if (!(0, chai_js_1.isImported)(context)) {
            return {};
        }
        return {
            ExpressionStatement(node) {
                const { expression } = node;
                checkExpect(context, expression);
                checkShould(context, expression);
                checkAssert(context, expression);
            },
        };
    },
};
function checkAssert(context, expression) {
    if (expression.type === 'CallExpression') {
        const { callee, arguments: args } = expression;
        if (callee.type === 'MemberExpression' && (0, ast_js_1.isIdentifier)(callee.object, 'assert')) {
            findDuplicates(context, args);
        }
    }
}
function checkExpect(context, expression) {
    let currentExpression = expression;
    let args = [];
    while (true) {
        if (currentExpression.type === 'CallExpression') {
            args = [...currentExpression.arguments, ...args];
            currentExpression = currentExpression.callee;
        }
        else if (currentExpression.type === 'MemberExpression') {
            currentExpression = currentExpression.object;
        }
        else if ((0, ast_js_1.isIdentifier)(currentExpression, 'expect')) {
            break;
        }
        else {
            return;
        }
    }
    findDuplicates(context, args);
}
function checkShould(context, expression) {
    let currentExpression = expression;
    let args = [];
    let hasShould = false;
    while (true) {
        if (currentExpression.type === 'CallExpression') {
            args = [...currentExpression.arguments, ...args];
            currentExpression = currentExpression.callee;
        }
        else if (currentExpression.type === 'MemberExpression') {
            if ((0, ast_js_1.isIdentifier)(currentExpression.property, 'should')) {
                hasShould = true;
            }
            currentExpression = currentExpression.object;
        }
        else if ((0, ast_js_1.isIdentifier)(currentExpression, 'should')) {
            break;
        }
        else if (hasShould) {
            args = [currentExpression, ...args];
            break;
        }
        else {
            return;
        }
    }
    findDuplicates(context, args);
}
function findDuplicates(context, args) {
    for (let i = 0; i < args.length; i++) {
        for (let j = i + 1; j < args.length; j++) {
            const duplicates = (0, equivalence_js_1.areEquivalent)(args[i], args[j], context.sourceCode);
            if (duplicates && !(0, ast_js_1.isLiteral)(args[i])) {
                (0, location_js_1.report)(context, { message: `Replace this argument or its duplicate.`, node: args[i] }, [
                    (0, location_js_1.toSecondaryLocation)(args[j]),
                ]);
            }
        }
    }
}
