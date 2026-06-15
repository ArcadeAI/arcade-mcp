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
// https://sonarsource.github.io/rspec/#/rspec/S2681/javascript
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
const meta = __importStar(require("./generated-meta.js"));
const NestingStatementLike = new Set([
    'IfStatement',
    'ForStatement',
    'ForInStatement',
    'ForOfStatement',
    'WhileStatement',
]);
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta),
    create(context) {
        return {
            Program: (node) => checkStatements(node.body, context),
            BlockStatement: (node) => checkStatements(node.body, context),
            TSModuleBlock: (node) => checkStatements(node.body, context),
        };
    },
};
function checkStatements(statements, context) {
    for (const unenclosedConsecutives of chain(statements).filter(chainedStatements => chainedStatements.areUnenclosed())) {
        if (unenclosedConsecutives.areAdjacent()) {
            raiseAdjacenceIssue(unenclosedConsecutives, context);
        }
        else if (unenclosedConsecutives.areBothIndented()) {
            raiseBlockIssue(unenclosedConsecutives, countStatementsInTheSamePile(unenclosedConsecutives.prev, statements), context);
        }
        else if (unenclosedConsecutives.areInlinedAndIndented()) {
            raiseInlineAndIndentedIssue(unenclosedConsecutives, context);
        }
    }
}
function chain(statements) {
    return statements
        .reduce((result, statement, i, array) => {
        if (i < array.length - 1 && isNestingStatement(statement)) {
            result.push({ prev: statement, next: array[i + 1] });
        }
        return result;
    }, new Array())
        .map(pair => {
        return new ChainedStatements(pair.prev, extractLastBody(pair.prev), pair.next);
    });
}
function extractLastBody(statement) {
    if (statement.type === 'IfStatement') {
        if (statement.alternate) {
            return statement.alternate;
        }
        else {
            return statement.consequent;
        }
    }
    else {
        return statement.body;
    }
}
function countStatementsInTheSamePile(reference, statements) {
    const startOfPile = position(reference).start;
    let lastLineOfPile = startOfPile.line;
    for (const statement of statements) {
        const currentPosition = position(statement);
        const currentLine = currentPosition.end.line;
        const currentIndentation = currentPosition.start.column;
        if (currentLine > startOfPile.line) {
            if (currentIndentation === startOfPile.column) {
                lastLineOfPile = currentPosition.end.line;
            }
            else {
                break;
            }
        }
    }
    return lastLineOfPile - startOfPile.line + 1;
}
function raiseAdjacenceIssue(adjacentStatements, context) {
    context.report({
        message: `This statement will not be executed ${adjacentStatements.includedStatementQualifier()}; only the first statement will be. ` +
            `The rest will execute ${adjacentStatements.excludedStatementsQualifier()}.`,
        node: adjacentStatements.next,
    });
}
function raiseBlockIssue(piledStatements, sizeOfPile, context) {
    context.report({
        message: `This line will not be executed ${piledStatements.includedStatementQualifier()}; only the first line of this ${sizeOfPile}-line block will be. ` +
            `The rest will execute ${piledStatements.excludedStatementsQualifier()}.`,
        node: piledStatements.next,
    });
}
function raiseInlineAndIndentedIssue(chainedStatements, context) {
    context.report({
        message: `This line will not be executed ${chainedStatements.includedStatementQualifier()}; only the first statement will be. ` +
            `The rest will execute ${chainedStatements.excludedStatementsQualifier()}.`,
        node: chainedStatements.next,
    });
}
function isNestingStatement(node) {
    return NestingStatementLike.has(node.type);
}
class ChainedStatements {
    constructor(topStatement, prev, next) {
        this.topStatement = topStatement;
        this.prev = prev;
        this.next = next;
        const topPosition = position(topStatement);
        const prevPosition = position(prev);
        const nextPosition = position(next);
        this.positions = {
            prevTopStart: topPosition.start,
            prevTopEnd: topPosition.end,
            prevStart: prevPosition.start,
            prevEnd: prevPosition.end,
            nextStart: nextPosition.start,
            nextEnd: nextPosition.end,
        };
    }
    areUnenclosed() {
        return this.prev.type !== 'BlockStatement';
    }
    areAdjacent() {
        return this.positions.prevEnd.line === this.positions.nextStart.line;
    }
    areBothIndented() {
        return (this.positions.prevStart.column === this.positions.nextStart.column && this.prevIsIndented());
    }
    areInlinedAndIndented() {
        return (this.positions.prevStart.line === this.positions.prevTopEnd.line &&
            this.positions.nextStart.column > this.positions.prevTopStart.column);
    }
    includedStatementQualifier() {
        return this.topStatement.type === 'IfStatement' ? 'conditionally' : 'in a loop';
    }
    excludedStatementsQualifier() {
        return this.topStatement.type === 'IfStatement' ? 'unconditionally' : 'only once';
    }
    prevIsIndented() {
        return this.positions.prevStart.column > this.positions.prevTopStart.column;
    }
}
function position(node) {
    return node.loc;
}
