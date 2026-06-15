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
// https://sonarsource.github.io/rspec/#/rspec/S2428
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
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const ast_js_1 = require("../helpers/ast.js");
const meta = __importStar(require("./generated-meta.js"));
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            declarePropertiesInsideObject: 'Declare one or more properties of this object inside of the object literal syntax instead of using separate statements.',
        },
    }),
    create(context) {
        return {
            BlockStatement: (node) => checkObjectInitialization(node.body, context),
            Program: (node) => {
                checkObjectInitialization((0, ast_js_1.getProgramStatements)(node), context);
            },
        };
    },
};
function checkObjectInitialization(statements, context) {
    let index = 0;
    while (index < statements.length - 1) {
        const objectDeclaration = getObjectDeclaration(statements[index]);
        if (objectDeclaration && (0, ast_js_1.isIdentifier)(objectDeclaration.id)) {
            const nextStmt = statements[index + 1];
            if (isPropertyAssignment(nextStmt, objectDeclaration.id, context.sourceCode)) {
                context.report({ messageId: 'declarePropertiesInsideObject', node: objectDeclaration });
            }
        }
        index++;
    }
}
function getObjectDeclaration(statement) {
    if (statement.type === 'VariableDeclaration') {
        return statement.declarations.find(declaration => !!declaration.init && isEmptyObjectExpression(declaration.init));
    }
    return undefined;
}
function isEmptyObjectExpression(expression) {
    return expression.type === 'ObjectExpression' && expression.properties.length === 0;
}
function isPropertyAssignment(statement, objectIdentifier, sourceCode) {
    if (statement.type === 'ExpressionStatement' &&
        statement.expression.type === 'AssignmentExpression') {
        const { left, right } = statement.expression;
        if (left.type === 'MemberExpression') {
            return (!left.computed &&
                isSingleLineExpression(right, sourceCode) &&
                (0, equivalence_js_1.areEquivalent)(left.object, objectIdentifier, sourceCode) &&
                !(0, equivalence_js_1.areEquivalent)(left.object, right, sourceCode));
        }
    }
    return false;
    function isSingleLineExpression(expression, sourceCode) {
        const first = sourceCode.getFirstToken(expression).loc;
        const last = sourceCode.getLastToken(expression).loc;
        return first.start.line === last.end.line;
    }
}
