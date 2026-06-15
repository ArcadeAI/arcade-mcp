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
// https://sonarsource.github.io/rspec/#/rspec/S1862
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
const location_js_1 = require("../helpers/location.js");
const meta = __importStar(require("./generated-meta.js"));
const duplicatedConditionMessage = 'This condition is covered by the one on line {{line}}';
const duplicatedCaseMessage = 'This case duplicates the one on line {{line}}';
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            duplicatedCondition: duplicatedConditionMessage,
            duplicatedCase: duplicatedCaseMessage,
        },
    }),
    create(context) {
        const { sourceCode } = context;
        return {
            IfStatement(node) {
                const { test } = node;
                const conditionsToCheck = test.type === 'LogicalExpression' && test.operator === '&&'
                    ? [test, ...splitByAnd(test)]
                    : [test];
                let current = node;
                let operandsToCheck = conditionsToCheck.map(c => splitByOr(c).map(splitByAnd));
                while (current.parent?.type === 'IfStatement' && current.parent.alternate === current) {
                    current = current.parent;
                    const currentOrOperands = splitByOr(current.test).map(splitByAnd);
                    operandsToCheck = operandsToCheck.map(orOperands => orOperands.filter(orOperand => !currentOrOperands.some(currentOrOperand => isSubset(currentOrOperand, orOperand, sourceCode))));
                    if (operandsToCheck.some(orOperands => orOperands.length === 0)) {
                        (0, location_js_1.report)(context, {
                            message: duplicatedConditionMessage,
                            messageId: 'duplicatedCondition',
                            data: { line: current.test.loc.start.line },
                            node: test,
                        }, [(0, location_js_1.toSecondaryLocation)({ loc: current.test.loc }, 'Covering')]);
                        break;
                    }
                }
            },
            SwitchStatement(switchStmt) {
                const previousTests = [];
                for (const switchCase of switchStmt.cases) {
                    if (switchCase.test) {
                        const { test } = switchCase;
                        const duplicateTest = previousTests.find(previousTest => (0, equivalence_js_1.areEquivalent)(test, previousTest, sourceCode));
                        if (duplicateTest) {
                            (0, location_js_1.report)(context, {
                                messageId: 'duplicatedCase',
                                message: duplicatedCaseMessage,
                                data: {
                                    line: duplicateTest.loc.start.line,
                                },
                                node: test,
                            }, [(0, location_js_1.toSecondaryLocation)({ loc: duplicateTest.loc }, 'Original')]);
                        }
                        else {
                            previousTests.push(test);
                        }
                    }
                }
            },
        };
    },
};
const splitByOr = splitByLogicalOperator.bind(null, '||');
const splitByAnd = splitByLogicalOperator.bind(null, '&&');
function splitByLogicalOperator(operator, node) {
    if (node.type === 'LogicalExpression' && node.operator === operator) {
        return [
            ...splitByLogicalOperator(operator, node.left),
            ...splitByLogicalOperator(operator, node.right),
        ];
    }
    return [node];
}
function isSubset(first, second, sourceCode) {
    return first.every(fst => second.some(snd => isSubsetOf(fst, snd, sourceCode)));
    function isSubsetOf(first, second, sourceCode) {
        if (first.type !== second.type) {
            return false;
        }
        if (first.type === 'LogicalExpression') {
            const second1 = second;
            if ((first.operator === '||' || first.operator === '&&') &&
                first.operator === second1.operator) {
                return ((isSubsetOf(first.left, second1.left, sourceCode) &&
                    isSubsetOf(first.right, second1.right, sourceCode)) ||
                    (isSubsetOf(first.left, second1.right, sourceCode) &&
                        isSubsetOf(first.right, second1.left, sourceCode)));
            }
        }
        return (0, equivalence_js_1.areEquivalent)(first, second, sourceCode);
    }
}
