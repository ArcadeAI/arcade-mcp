"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.getFullyQualifiedNameTS = getFullyQualifiedNameTS;
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
const typescript_1 = __importDefault(require("typescript"));
const ancestor_js_1 = require("./ancestor.js");
const module_js_1 = require("./module.js");
function getFullyQualifiedNameTS(services, rootNode) {
    const result = [];
    let node = rootNode;
    const visitedNodes = new Set();
    while (node) {
        if (visitedNodes.has(node)) {
            return null;
        }
        visitedNodes.add(node);
        switch (node.kind) {
            case typescript_1.default.SyntaxKind.CallExpression: {
                const callExpressionNode = node;
                if (isRequireCall(callExpressionNode)) {
                    node = callExpressionNode.arguments.at(0);
                }
                else {
                    node = callExpressionNode.expression;
                }
                break;
            }
            case typescript_1.default.SyntaxKind.FunctionDeclaration: {
                const functionDeclarationNode = node;
                const name = functionDeclarationNode.name?.text;
                if (!name) {
                    return null;
                }
                result.push(name);
                node = functionDeclarationNode.parent;
                break;
            }
            case typescript_1.default.SyntaxKind.PropertyAccessExpression: {
                const propertyAccessExpression = node;
                const rhsFQN = propertyAccessExpression.name.text;
                if (!rhsFQN) {
                    return null;
                }
                result.push(rhsFQN);
                node = propertyAccessExpression.expression;
                break;
            }
            case typescript_1.default.SyntaxKind.ImportSpecifier: {
                const importSpecifier = node;
                const identifierName = importSpecifier.propertyName?.text ?? importSpecifier.name.text;
                if (!identifierName) {
                    return null;
                }
                result.push(identifierName);
                node = importSpecifier.parent;
                break;
            }
            case typescript_1.default.SyntaxKind.NamespaceImport: {
                node = node.parent;
                break;
            }
            case typescript_1.default.SyntaxKind.ImportDeclaration: {
                node = node.moduleSpecifier;
                break;
            }
            case typescript_1.default.SyntaxKind.SourceFile: {
                // Don't generate fqn for local files
                return null;
            }
            case typescript_1.default.SyntaxKind.BindingElement: {
                const bindingElement = node;
                let identifier;
                if (bindingElement.propertyName && 'text' in bindingElement.propertyName) {
                    identifier = bindingElement.propertyName.text;
                }
                else if ('text' in bindingElement.name) {
                    identifier = bindingElement.name.text;
                }
                if (!identifier) {
                    return null;
                }
                result.push(identifier);
                node = node.parent;
                break;
            }
            case typescript_1.default.SyntaxKind.VariableDeclaration: {
                const variableDeclaration = node;
                if (variableDeclaration.initializer) {
                    node = variableDeclaration.initializer;
                    break;
                }
                else {
                    return null;
                }
            }
            case typescript_1.default.SyntaxKind.Identifier: {
                const identifierSymbol = services.program.getTypeChecker().getSymbolAtLocation(node);
                const declaration = identifierSymbol?.declarations?.at(0);
                // Handle: no symbol info, compiler module, self-referential declaration (e.g., `module` in CommonJS),
                // or declaration that contains the root node (e.g., `const geo = geo(request)` where import is shadowed)
                if (isCompilerModule(identifierSymbol) ||
                    !declaration ||
                    declaration === node ||
                    (0, ancestor_js_1.isTsAncestor)(declaration, rootNode)) {
                    result.push(node.text);
                    return returnResult();
                }
                else {
                    node = declaration;
                    break;
                }
            }
            case typescript_1.default.SyntaxKind.StringLiteral: {
                result.push(node.text);
                return returnResult();
            }
            case typescript_1.default.SyntaxKind.ImportClause: // Fallthrough
            case typescript_1.default.SyntaxKind.ObjectBindingPattern: // Fallthrough
            case typescript_1.default.SyntaxKind.Block: // Fallthrough
            case typescript_1.default.SyntaxKind.ExpressionStatement: // Fallthrough
            case typescript_1.default.SyntaxKind.NamedImports: // Fallthrough
            case typescript_1.default.SyntaxKind.ModuleBlock: {
                node = node.parent;
                break;
            }
            default: {
                return null;
            }
        }
    }
    return null;
    function returnResult() {
        result.reverse();
        return (0, module_js_1.removeNodePrefixIfExists)(result.join('.'));
    }
}
function isRequireCall(callExpression) {
    return (callExpression.expression.kind === typescript_1.default.SyntaxKind.Identifier &&
        callExpression.expression.text === 'require' &&
        callExpression.arguments.length === 1);
}
function isCompilerModule(node) {
    return (node &&
        (node.flags & typescript_1.default.SymbolFlags.Module) !== 0 &&
        (node.flags & typescript_1.default.SymbolFlags.Assignment) !== 0);
}
