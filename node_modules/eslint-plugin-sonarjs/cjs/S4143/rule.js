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
// https://sonarsource.github.io/rspec/#/rspec/S4143
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
const location_js_1 = require("../helpers/location.js");
const meta = __importStar(require("./generated-meta.js"));
const message = 'Verify this is the index that was intended; "{{index}}" was already set on line {{line}}.';
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            verifyIntendedIndex: message,
        },
    }),
    create(context) {
        return {
            SwitchCase(node) {
                checkStatements(node.consequent);
            },
            BlockStatement(node) {
                checkStatements(node.body);
            },
            Program(node) {
                checkStatements((0, ast_js_1.getProgramStatements)(node));
            },
        };
        function checkStatements(statements) {
            const usedKeys = new Map();
            let collection;
            for (const statement of statements) {
                const keyWriteUsage = getKeyWriteUsage(statement);
                if (keyWriteUsage) {
                    if (collection &&
                        !(0, equivalence_js_1.areEquivalent)(keyWriteUsage.collectionNode, collection, context.sourceCode)) {
                        usedKeys.clear();
                    }
                    const sameKeyWriteUsage = usedKeys.get(keyWriteUsage.indexOrKey);
                    if (sameKeyWriteUsage?.node.loc) {
                        const secondaryLocations = [
                            (0, location_js_1.toSecondaryLocation)(sameKeyWriteUsage.node, 'Original value'),
                        ];
                        (0, location_js_1.report)(context, {
                            node: keyWriteUsage.node,
                            messageId: 'verifyIntendedIndex',
                            message,
                            data: {
                                index: keyWriteUsage.indexOrKey,
                                line: sameKeyWriteUsage.node.loc.start.line,
                            },
                        }, secondaryLocations);
                    }
                    usedKeys.set(keyWriteUsage.indexOrKey, keyWriteUsage);
                    collection = keyWriteUsage.collectionNode;
                }
                else {
                    usedKeys.clear();
                }
            }
        }
        function getKeyWriteUsage(node) {
            if (node.type === 'ExpressionStatement') {
                return arrayKeyWriteUsage(node.expression) || mapOrSetKeyWriteUsage(node.expression);
            }
            return undefined;
        }
        function arrayKeyWriteUsage(node) {
            // a[b] = ...
            if (isSimpleAssignment(node) && node.left.type === 'MemberExpression' && node.left.computed) {
                const { left, right } = node;
                const index = extractIndex(left.property);
                if (index !== undefined && !isUsed(left.object, right)) {
                    return {
                        collectionNode: left.object,
                        indexOrKey: index,
                        node,
                    };
                }
            }
            return undefined;
        }
        function isUsed(value, expression) {
            const valueTokens = context.sourceCode.getTokens(value);
            const expressionTokens = context.sourceCode.getTokens(expression);
            const foundUsage = expressionTokens.find((token, index) => {
                if (eq(token, valueTokens[0])) {
                    for (let expressionIndex = index, valueIndex = 0; expressionIndex < expressionTokens.length && valueIndex < valueTokens.length; expressionIndex++, valueIndex++) {
                        if (!eq(expressionTokens[expressionIndex], valueTokens[valueIndex])) {
                            break;
                        }
                        else if (valueIndex === valueTokens.length - 1) {
                            return true;
                        }
                    }
                }
                return false;
            });
            return foundUsage !== undefined;
        }
    },
};
function eq(token1, token2) {
    return token1.value === token2.value;
}
function isSimpleAssignment(node) {
    return node.type === 'AssignmentExpression' && node.operator === '=';
}
function extractIndex(node) {
    if ((0, ast_js_1.isLiteral)(node)) {
        const { value } = node;
        return typeof value === 'number' || typeof value === 'string' ? String(value) : undefined;
    }
    else if ((0, ast_js_1.isIdentifier)(node)) {
        return node.name;
    }
    return undefined;
}
function mapOrSetKeyWriteUsage(node) {
    if (node.type === 'CallExpression' && node.callee.type === 'MemberExpression') {
        const propertyAccess = node.callee;
        if ((0, ast_js_1.isIdentifier)(propertyAccess.property)) {
            const methodName = propertyAccess.property.name;
            const addMethod = methodName === 'add' && node.arguments.length === 1;
            const setMethod = methodName === 'set' && node.arguments.length === 2;
            if (addMethod || setMethod) {
                const key = extractIndex(node.arguments[0]);
                if (key) {
                    return {
                        collectionNode: propertyAccess.object,
                        indexOrKey: key,
                        node,
                    };
                }
            }
        }
    }
    return undefined;
}
