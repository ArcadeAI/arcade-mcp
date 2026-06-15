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
// https://sonarsource.github.io/rspec/#/rspec/S7059/javascript
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
const parser_services_js_1 = require("../helpers/parser-services.js");
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const type_js_1 = require("../helpers/type.js");
const ast_js_1 = require("../helpers/ast.js");
const meta = __importStar(require("./generated-meta.js"));
const flaggedStatements = new Set();
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            noAsyncConstructor: 'Refactor this asynchronous operation outside of the constructor.',
        },
    }),
    create(context) {
        const services = context.sourceCode.parserServices;
        if (!(0, parser_services_js_1.isRequiredParserServices)(services)) {
            return {};
        }
        /**
         * Given a Promise call, get the parent statement of the async call.
         * We want to ensure that it is inside a constructor, but not part of a function declaration:
         * constructor() {
         *  foo();
         * }
         * and not
         * constructor() {
         *  myFunction = () => { foo() }
         * }
         * @param node : promise call
         */
        function asyncStatementInsideConstructor(node) {
            let classConstructor;
            let statement;
            for (const ancestor of context.sourceCode.getAncestors(node)) {
                if (ancestor.type === 'MethodDefinition' && ancestor.kind === 'constructor') {
                    classConstructor = ancestor;
                }
                if (classConstructor && ancestor.type.endsWith('Statement')) {
                    statement = ancestor;
                }
                // If we find a function declaration it should not be considered as part of the constructor
                if (classConstructor && statement && (0, ast_js_1.isFunctionNode)(ancestor)) {
                    statement = undefined;
                    classConstructor = undefined;
                }
            }
            return statement;
        }
        return {
            CallExpression(node) {
                if (!(0, type_js_1.isThenable)(node, services)) {
                    return;
                }
                // we want to raise on the parent statement
                const statement = asyncStatementInsideConstructor(node);
                if (statement && !flaggedStatements.has(statement)) {
                    flaggedStatements.add(statement);
                    context.report({
                        node: statement,
                        messageId: 'noAsyncConstructor',
                    });
                }
            },
            'Program:exit'() {
                flaggedStatements.clear();
            },
        };
    },
};
