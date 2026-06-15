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
// https://sonarsource.github.io/rspec/#/rspec/S1871
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
const conditions_js_1 = require("../helpers/conditions.js");
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const ast_js_1 = require("../helpers/ast.js");
const collection_js_1 = require("../helpers/collection.js");
const location_js_1 = require("../helpers/location.js");
const meta = __importStar(require("./generated-meta.js"));
const message = "This {{type}}'s code block is the same as the block for the {{type}} on line {{line}}.";
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            sameConditionalBlock: message,
        },
    }),
    create(context) {
        return {
            IfStatement(node) {
                visitIfStatement(node);
            },
            SwitchStatement(node) {
                visitSwitchStatement(node);
            },
        };
        function visitIfStatement(ifStmt) {
            if ((0, ast_js_1.isIfStatement)(ifStmt.parent)) {
                return;
            }
            const { branches, endsWithElse } = (0, conditions_js_1.collectIfBranches)(ifStmt);
            if (allEquivalentWithoutDefault(branches, endsWithElse)) {
                for (const [i, branch] of branches.slice(1).entries()) {
                    reportIssue(branch, branches[i], 'branch');
                }
                return;
            }
            for (let i = 1; i < branches.length; i++) {
                if (hasRequiredSize([branches[i]])) {
                    for (let j = 0; j < i; j++) {
                        if (compareIfBranches(branches[i], branches[j])) {
                            break;
                        }
                    }
                }
            }
        }
        function visitSwitchStatement(switchStmt) {
            const { cases } = switchStmt;
            const { endsWithDefault } = (0, conditions_js_1.collectSwitchBranches)(switchStmt);
            const nonEmptyCases = cases.filter(c => (0, conditions_js_1.takeWithoutBreak)(expandSingleBlockStatement(c.consequent)).length > 0);
            const casesWithoutBreak = nonEmptyCases.map(c => (0, conditions_js_1.takeWithoutBreak)(expandSingleBlockStatement(c.consequent)));
            if (allEquivalentWithoutDefault(casesWithoutBreak, endsWithDefault)) {
                for (const [i, caseStmt] of nonEmptyCases.slice(1).entries()) {
                    reportIssue(caseStmt, nonEmptyCases[i], 'case');
                }
                return;
            }
            for (let i = 1; i < cases.length; i++) {
                const firstClauseWithoutBreak = (0, conditions_js_1.takeWithoutBreak)(expandSingleBlockStatement(cases[i].consequent));
                if (hasRequiredSize(firstClauseWithoutBreak)) {
                    for (let j = 0; j < i; j++) {
                        const secondClauseWithoutBreak = (0, conditions_js_1.takeWithoutBreak)(expandSingleBlockStatement(cases[j].consequent));
                        if ((0, equivalence_js_1.areEquivalent)(firstClauseWithoutBreak, secondClauseWithoutBreak, context.sourceCode)) {
                            reportIssue(cases[i], cases[j], 'case');
                            break;
                        }
                    }
                }
            }
        }
        function hasRequiredSize(nodes) {
            if (nodes.length > 0) {
                const tokens = [
                    ...context.sourceCode.getTokens(nodes[0]),
                    ...context.sourceCode.getTokens((0, collection_js_1.last)(nodes)),
                ].filter(token => token.value !== '{' && token.value !== '}');
                return tokens.length > 0 && (0, collection_js_1.last)(tokens).loc.end.line > tokens[0].loc.start.line;
            }
            return false;
        }
        function compareIfBranches(a, b) {
            const equivalent = (0, equivalence_js_1.areEquivalent)(a, b, context.sourceCode);
            if (equivalent && b.loc) {
                reportIssue(a, b, 'branch');
            }
            return equivalent;
        }
        function allEquivalentWithoutDefault(branches, endsWithDefault) {
            return (!endsWithDefault &&
                branches.length > 1 &&
                branches
                    .slice(1)
                    .every((branch, index) => (0, equivalence_js_1.areEquivalent)(branch, branches[index], context.sourceCode)));
        }
        function reportIssue(node, equivalentNode, type) {
            const equivalentNodeLoc = equivalentNode.loc;
            (0, location_js_1.report)(context, {
                message,
                messageId: 'sameConditionalBlock',
                data: { type, line: String(equivalentNodeLoc.start.line) },
                node,
            }, [(0, location_js_1.toSecondaryLocation)(equivalentNode, 'Original')]);
        }
    },
};
function expandSingleBlockStatement(nodes) {
    if (nodes.length === 1) {
        const node = nodes[0];
        if (node.type === 'BlockStatement') {
            return node.body;
        }
    }
    return nodes;
}
