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
// https://sonarsource.github.io/rspec/#/rspec/S2251/javascript
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
const location_js_1 = require("../helpers/location.js");
const meta = __importStar(require("./generated-meta.js"));
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta),
    create(context) {
        return {
            ForStatement: (node) => {
                const forStatement = node;
                const test = forStatement.test;
                const loopIncrement = ForLoopIncrement.findInLoopUpdate(forStatement);
                if (test == null || loopIncrement == null || forStatement.update == null) {
                    return;
                }
                const wrongDirection = getWrongDirection(test, loopIncrement);
                if (wrongDirection !== 0 && wrongDirection === loopIncrement.direction) {
                    const movement = wrongDirection > 0 ? 'incremented' : 'decremented';
                    (0, location_js_1.report)(context, {
                        message: `"${loopIncrement.identifier.name}" is ${movement} and will never reach its stop condition.`,
                        node: forStatement.update,
                    }, [(0, location_js_1.toSecondaryLocation)(test)]);
                }
            },
        };
    },
};
class ForLoopIncrement {
    constructor(increment, identifier, direction) {
        this.increment = increment;
        this.identifier = identifier;
        this.direction = direction;
    }
    static findInLoopUpdate(forStatement) {
        let result = null;
        const expression = forStatement.update;
        if (!expression) {
            return null;
        }
        if (expression.type === 'UpdateExpression') {
            const updateExpression = expression;
            const direction = updateExpression.operator === '++' ? 1 : -1;
            result = ForLoopIncrement.increment(updateExpression, updateExpression.argument, direction);
        }
        if (expression.type === 'AssignmentExpression') {
            const assignmentExpression = expression;
            if (assignmentExpression.operator === '+=' &&
                assignmentExpression.left.type === 'Identifier') {
                result = ForLoopIncrement.increment(expression, assignmentExpression.left, directionFromValue(assignmentExpression.right));
            }
            if (assignmentExpression.operator === '-=' &&
                assignmentExpression.left.type === 'Identifier') {
                result = ForLoopIncrement.increment(expression, assignmentExpression.left, -directionFromValue(assignmentExpression.right));
            }
            if (assignmentExpression.operator === '=') {
                result = ForLoopIncrement.assignmentIncrement(assignmentExpression);
            }
        }
        return result;
    }
    static increment(increment, expression, direction) {
        if (expression.type === 'Identifier') {
            return new ForLoopIncrement(increment, expression, direction);
        }
        return null;
    }
    static assignmentIncrement(assignmentExpression) {
        const lhs = assignmentExpression.left;
        const rhs = assignmentExpression.right;
        if (lhs.type === 'Identifier' &&
            rhs.type === 'BinaryExpression' &&
            (rhs.operator === '+' || rhs.operator === '-')) {
            let incrementDirection = directionFromValue(rhs.right);
            if (incrementDirection !== null && isSameIdentifier(rhs.left, lhs)) {
                incrementDirection = rhs.operator === '-' ? -incrementDirection : incrementDirection;
                return ForLoopIncrement.increment(assignmentExpression, lhs, incrementDirection);
            }
        }
        return null;
    }
}
function directionFromValue(expression) {
    if (expression.type === 'Literal') {
        const value = Number(expression.raw);
        if (Number.isNaN(value) || value === 0) {
            return 0;
        }
        return value > 0 ? 1 : -1;
    }
    if (expression.type === 'UnaryExpression') {
        const unaryExpression = expression;
        if (unaryExpression.operator === '+') {
            return directionFromValue(unaryExpression.argument);
        }
        if (unaryExpression.operator === '-') {
            return -directionFromValue(unaryExpression.argument);
        }
    }
    return 0;
}
function getWrongDirection(condition, forLoopIncrement) {
    if (condition.type !== 'BinaryExpression') {
        return 0;
    }
    if (isSameIdentifier(condition.left, forLoopIncrement.identifier)) {
        if (condition.operator === '<' || condition.operator === '<=') {
            return -1;
        }
        if (condition.operator === '>' || condition.operator === '>=') {
            return +1;
        }
    }
    else if (isSameIdentifier(condition.right, forLoopIncrement.identifier)) {
        if (condition.operator === '<' || condition.operator === '<=') {
            return +1;
        }
        if (condition.operator === '>' || condition.operator === '>=') {
            return -1;
        }
    }
    return 0;
}
function isSameIdentifier(expression, identifier) {
    return expression.type === 'Identifier' && expression.name === identifier.name;
}
