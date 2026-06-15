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
// https://sonarsource.github.io/rspec/#/rspec/S3801/javascript
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
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.rule = void 0;
const typescript_1 = __importDefault(require("typescript"));
const parser_services_js_1 = require("../helpers/parser-services.js");
const type_js_1 = require("../helpers/type.js");
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const location_js_1 = require("../helpers/location.js");
const ancestor_js_1 = require("../helpers/ancestor.js");
const meta = __importStar(require("./generated-meta.js"));
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta),
    create(context) {
        const sourceCode = context.sourceCode;
        const services = sourceCode.parserServices;
        const hasTypeInformation = (0, parser_services_js_1.isRequiredParserServices)(services);
        const functionContextStack = [];
        const checkOnFunctionExit = (node) => checkFunctionLikeDeclaration(node, functionContextStack.at(-1), hasTypeInformation ? services : undefined);
        // tracks the segments we've traversed in the current code path
        let currentSegments;
        // tracks all current segments for all open paths
        const allCurrentSegments = [];
        function checkFunctionLikeDeclaration(node, functionContext, services) {
            if (!functionContext ||
                (!!node.returnType &&
                    declaredReturnTypeContainsVoidOrNeverTypes(node.returnType.typeAnnotation))) {
                return;
            }
            checkFunctionForImplicitReturn(functionContext, services);
            if (hasInconsistentReturns(functionContext)) {
                const secondaryLocations = getSecondaryLocations(functionContext, node);
                (0, location_js_1.report)(context, {
                    message: `Refactor this function to use "return" consistently.`,
                    loc: (0, location_js_1.getMainFunctionTokenLocation)(node, (0, ancestor_js_1.getParent)(context, node), context),
                }, secondaryLocations);
            }
        }
        function checkFunctionForImplicitReturn(functionContext, services) {
            // As this method is called at the exit point of a function definition, the current
            // segments are the ones leading to the exit point at the end of the function. If they
            // are reachable, it means there is an implicit return.
            const hasReachableSegment = Array.from(currentSegments).some(segment => segment.reachable);
            if (hasReachableSegment && services) {
                // Check if any exhaustive switch makes the implicit return unreachable.
                // A switch eliminates the implicit return if:
                // 1. It's exhaustive (covers all possible values)
                // 2. Its last case doesn't have a reachable exit (all paths return/throw)
                const hasExhaustiveSwitch = functionContext.switchStatements.some(switchStmt => isExhaustiveSwitch(switchStmt, services) &&
                    !functionContext.switchLastCaseReachable.get(switchStmt));
                // Check if the last call expression returns 'never' (e.g., a throwing function)
                // If so, the implicit return is unreachable
                const lastCallReturnsNever = functionContext.lastCallExpression &&
                    isNeverReturningCall(functionContext.lastCallExpression, services);
                functionContext.containsImplicitReturn = !hasExhaustiveSwitch && !lastCallReturnsNever;
            }
            else {
                functionContext.containsImplicitReturn = hasReachableSegment;
            }
        }
        function getSecondaryLocations(functionContext, node) {
            const secondaryLocations = functionContext.returnStatements
                .slice()
                .map(returnStatement => (0, location_js_1.toSecondaryLocation)(returnStatement, returnStatement.argument ? 'Return with value' : 'Return without value'));
            if (functionContext.containsImplicitReturn) {
                const closeCurlyBraceToken = sourceCode.getLastToken(node, token => token.value === '}');
                if (!!closeCurlyBraceToken) {
                    secondaryLocations.push((0, location_js_1.toSecondaryLocation)(closeCurlyBraceToken, 'Implicit return without value'));
                }
            }
            return secondaryLocations;
        }
        return {
            onCodePathStart(codePath) {
                functionContextStack.push({
                    codePath,
                    containsReturnWithValue: false,
                    containsReturnWithoutValue: false,
                    containsImplicitReturn: false,
                    returnStatements: [],
                    switchStatements: [],
                    switchLastCaseReachable: new Map(),
                    lastCallExpression: null,
                });
                allCurrentSegments.push(currentSegments);
                currentSegments = new Set();
            },
            onCodePathEnd() {
                functionContextStack.pop();
                currentSegments = allCurrentSegments.pop();
            },
            onCodePathSegmentStart(segment) {
                currentSegments.add(segment);
            },
            onCodePathSegmentEnd(segment) {
                currentSegments.delete(segment);
            },
            onUnreachableCodePathSegmentStart(segment) {
                currentSegments.add(segment);
            },
            onUnreachableCodePathSegmentEnd(segment) {
                currentSegments.delete(segment);
            },
            ReturnStatement(node) {
                const currentContext = functionContextStack.at(-1);
                if (!!currentContext) {
                    const returnStatement = node;
                    currentContext.containsReturnWithValue =
                        currentContext.containsReturnWithValue || !!returnStatement.argument;
                    currentContext.containsReturnWithoutValue =
                        currentContext.containsReturnWithoutValue || !returnStatement.argument;
                    currentContext.returnStatements.push(returnStatement);
                }
            },
            SwitchStatement(node) {
                const currentContext = functionContextStack.at(-1);
                if (currentContext) {
                    currentContext.switchStatements.push(node);
                }
            },
            'SwitchCase:exit'(node) {
                const currentContext = functionContextStack.at(-1);
                if (!currentContext) {
                    return;
                }
                const switchStmt = (0, ancestor_js_1.getParent)(context, node);
                const lastCase = switchStmt.cases.at(-1);
                // Only track the last case - all fall-throughs eventually reach it
                if (node === lastCase) {
                    const hasReachableExit = Array.from(currentSegments).some(s => s.reachable);
                    currentContext.switchLastCaseReachable.set(switchStmt, hasReachableExit);
                }
            },
            ExpressionStatement(node) {
                const currentContext = functionContextStack.at(-1);
                if (currentContext) {
                    const expr = node.expression;
                    if (expr.type === 'CallExpression') {
                        // Track any call expression - we'll check if it returns 'never' later
                        currentContext.lastCallExpression = expr;
                    }
                }
            },
            'FunctionDeclaration:exit': checkOnFunctionExit,
            'FunctionExpression:exit': checkOnFunctionExit,
            'ArrowFunctionExpression:exit': checkOnFunctionExit,
        };
    },
};
function hasInconsistentReturns(functionContext) {
    return (functionContext.containsReturnWithValue &&
        (functionContext.containsReturnWithoutValue || functionContext.containsImplicitReturn));
}
function declaredReturnTypeContainsVoidOrNeverTypes(returnTypeNode) {
    return (isVoidType(returnTypeNode) ||
        (returnTypeNode.type === 'TSUnionType' &&
            returnTypeNode.types.some(declaredReturnTypeContainsVoidOrNeverTypes)));
}
function isVoidType(typeNode) {
    return (typeNode.type === 'TSUndefinedKeyword' ||
        typeNode.type === 'TSVoidKeyword' ||
        typeNode.type === 'TSNeverKeyword');
}
/**
 * Checks if a switch statement is exhaustive (covers all possible values).
 * If exhaustive, ESLint's "implicit return" detection is a false positive
 * because the "no case matches" path doesn't actually exist.
 */
function isExhaustiveSwitch(switchStmt, services) {
    if (switchStmt.cases.length === 0) {
        return false;
    }
    // If there's a default case, the switch handles all possible values
    if (switchStmt.cases.some(c => c.test === null)) {
        return true;
    }
    // Without a default, verify all union/enum members are covered
    const discriminantType = (0, type_js_1.getTypeFromTreeNode)(switchStmt.discriminant, services);
    const types = discriminantType.isUnion() ? discriminantType.types : [discriminantType];
    // Must be a union or enum type to be exhaustive without a default
    if (types.length <= 1 && !isEnumType(discriminantType)) {
        return false;
    }
    // Collect all case test values
    const coveredTypes = new Set();
    for (const caseClause of switchStmt.cases) {
        if (caseClause.test) {
            const testType = (0, type_js_1.getTypeFromTreeNode)(caseClause.test, services);
            if (testType.isUnion()) {
                testType.types.forEach(t => coveredTypes.add(t));
            }
            else {
                coveredTypes.add(testType);
            }
        }
    }
    // Check if all types are covered
    const checker = services.program.getTypeChecker();
    return types.every(type => Array.from(coveredTypes).some(covered => checker.isTypeAssignableTo(type, covered)));
}
function isEnumType(type) {
    return ((type.flags & typescript_1.default.TypeFlags.EnumLike) !== 0 ||
        (type.flags & typescript_1.default.TypeFlags.EnumLiteral) !== 0 ||
        type.symbol?.flags === typescript_1.default.SymbolFlags.EnumMember);
}
/**
 * Checks if a call expression returns 'never' (e.g., a function that always throws).
 * This helps detect when an implicit return is actually unreachable because the
 * last statement calls a function that never returns.
 */
function isNeverReturningCall(callExpr, services) {
    const signature = (0, type_js_1.getSignatureFromCallee)(callExpr, services);
    if (!signature) {
        return false;
    }
    const returnType = signature.getReturnType();
    return (returnType.flags & typescript_1.default.TypeFlags.Never) !== 0;
}
