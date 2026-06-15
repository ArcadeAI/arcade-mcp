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
// https://sonarsource.github.io/rspec/#/rspec/S3514/javascript
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
const ancestor_js_1 = require("../helpers/ancestor.js");
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const ast_js_1 = require("../helpers/ast.js");
const location_js_1 = require("../helpers/location.js");
const meta = __importStar(require("./generated-meta.js"));
const MAX_INDEX = 4;
const isAllowedIndex = (idx) => idx >= 0 && idx <= MAX_INDEX;
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta),
    create(context) {
        function visitStatements(statements) {
            const declarationsByObject = new Map();
            for (const statement of statements) {
                if (statement.type === 'VariableDeclaration') {
                    visitDeclarations(declarationsByObject, statement.declarations);
                }
                else {
                    checkDeclarationsBlock(declarationsByObject);
                    declarationsByObject.clear();
                }
            }
            checkDeclarationsBlock(declarationsByObject);
        }
        function visitDeclarations(declarationsByObject, declarations) {
            for (const declaration of declarations) {
                const id = declaration.id;
                if (declaration.init && id.type === 'Identifier') {
                    const varName = id.name;
                    const expression = declaration.init;
                    if (expression.type !== 'MemberExpression') {
                        continue;
                    }
                    const property = expression.property;
                    if ((0, ast_js_1.isIdentifier)(property, varName) ||
                        ((0, ast_js_1.isNumberLiteral)(property) && isAllowedIndex(property.value))) {
                        addDeclaration(declarationsByObject, expression.object, declaration);
                    }
                }
            }
        }
        function addDeclaration(declarationsByObject, object, declaration) {
            const key = context.sourceCode.getText(object);
            const value = declarationsByObject.get(key);
            if (value) {
                value.push(declaration);
            }
            else {
                declarationsByObject.set(key, [declaration]);
            }
        }
        function checkDeclarationsBlock(declarationsByObject) {
            for (const [key, declarations] of declarationsByObject) {
                if (declarations.length > 1) {
                    const firstKind = getKind(declarations[0]);
                    const tail = declarations.slice(1);
                    if (tail.every(decl => getKind(decl) === firstKind)) {
                        (0, location_js_1.report)(context, {
                            node: declarations[0],
                            message: `Use destructuring syntax for these assignments from "${key}".`,
                        }, tail.map(node => (0, location_js_1.toSecondaryLocation)(node, 'Replace this assignment.')));
                    }
                }
            }
        }
        return {
            BlockStatement: (node) => {
                visitStatements(node.body);
            },
            SwitchCase: (node) => {
                visitStatements(node.consequent);
            },
            Program: (node) => {
                visitStatements(node.body);
            },
        };
    },
};
function getKind(declarator) {
    const declaration = (0, ancestor_js_1.findFirstMatchingAncestor)(declarator, n => n.type === 'VariableDeclaration');
    return declaration?.kind;
}
