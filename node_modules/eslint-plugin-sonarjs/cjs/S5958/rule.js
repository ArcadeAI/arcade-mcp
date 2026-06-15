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
// https://sonarsource.github.io/rspec/#/rspec/S5958/javascript
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
const reaching_definitions_js_1 = require("../helpers/reaching-definitions.js");
const ast_js_1 = require("../helpers/ast.js");
const mocha_js_1 = require("../helpers/mocha.js");
const meta = __importStar(require("./generated-meta.js"));
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta),
    create(context) {
        let catchWithDone = false;
        function isInsideTest(node) {
            return context.sourceCode
                .getAncestors(node)
                .some(n => n.type === 'CallExpression' && (0, mocha_js_1.isTestConstruct)(n));
        }
        return {
            'CatchClause CallExpression[callee.name="done"]': (_node) => {
                catchWithDone = true;
            },
            'CatchClause:exit': (node) => {
                if (!catchWithDone || !isInsideTest(node)) {
                    return;
                }
                catchWithDone = false;
                const { param } = node;
                if (param?.type === 'Identifier') {
                    const exception = (0, reaching_definitions_js_1.getVariableFromIdentifier)(param, context.sourceCode.getScope(node));
                    if (exception?.references.length === 0) {
                        context.report({
                            node: param,
                            message: 'Either the exception should be passed to "done(e)", or the exception should be tested further.',
                        });
                    }
                }
            },
            CallExpression(node) {
                const callExpr = node;
                if (isInsideTest(node) &&
                    isThrowAssertWithoutNot(callExpr) &&
                    (callExpr.arguments.length === 0 ||
                        (callExpr.arguments.length === 1 && (0, ast_js_1.isIdentifier)(callExpr.arguments[0], 'Error')))) {
                    context.report({
                        node: callExpr.callee.property,
                        message: 'Assert more concrete exception type or assert the message of exception.',
                    });
                }
            },
        };
    },
};
// find nodes in shape expect(...).a.b.c.throw() or a.should.throw()
function isThrowAssertWithoutNot(node) {
    if (node.callee.type !== 'MemberExpression') {
        return false;
    }
    let { object, property } = node.callee;
    if (!(0, ast_js_1.isIdentifier)(property, 'throw')) {
        return false;
    }
    while (object.type === 'MemberExpression') {
        if ((0, ast_js_1.isIdentifier)(object.property, 'not')) {
            return false;
        }
        if ((0, ast_js_1.isIdentifier)(object.property, 'should')) {
            return true;
        }
        object = object.object;
    }
    return object.type === 'CallExpression' && (0, ast_js_1.isIdentifier)(object.callee, 'expect');
}
