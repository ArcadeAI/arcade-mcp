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
// https://sonarsource.github.io/rspec/#/rspec/S3760/javascript
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
const location_js_1 = require("../helpers/location.js");
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const type_js_1 = require("../helpers/type.js");
const parser_services_js_1 = require("../helpers/parser-services.js");
const meta = __importStar(require("./generated-meta.js"));
const MESSAGE = 'Convert this operand into a number.';
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta),
    create(context) {
        const services = context.sourceCode.parserServices;
        if (!(0, parser_services_js_1.isRequiredParserServices)(services)) {
            return {};
        }
        return {
            BinaryExpression: (node) => {
                const binaryExpression = node;
                const operator = binaryExpression.operator;
                const leftType = (0, type_js_1.getTypeFromTreeNode)(binaryExpression.left, services);
                const rightType = (0, type_js_1.getTypeFromTreeNode)(binaryExpression.right, services);
                if (operator === '+') {
                    checkPlus(leftType, rightType, binaryExpression, context);
                }
                if (operator === '<' || operator === '>' || operator === '<=' || operator === '>=') {
                    checkComparison(leftType, rightType, binaryExpression, context);
                }
                if (operator === '-' || operator === '*' || operator === '/' || operator === '%') {
                    checkArithmetic(leftType, rightType, binaryExpression, context);
                }
            },
            AssignmentExpression: (node) => {
                const assignmentExpression = node;
                const operator = assignmentExpression.operator;
                const leftType = (0, type_js_1.getTypeFromTreeNode)(assignmentExpression.left, services);
                const rightType = (0, type_js_1.getTypeFromTreeNode)(assignmentExpression.right, services);
                if (operator === '+=') {
                    checkPlus(leftType, rightType, assignmentExpression, context);
                }
                if (operator === '-=' || operator === '*=' || operator === '/=' || operator === '%=') {
                    checkArithmetic(leftType, rightType, assignmentExpression, context);
                }
            },
            'UnaryExpression[operator="-"]': (node) => {
                const unaryExpression = node;
                const type = (0, type_js_1.getTypeFromTreeNode)(unaryExpression.argument, services);
                if (isBooleanStringOrDate(type)) {
                    (0, location_js_1.report)(context, {
                        node: unaryExpression.argument,
                        message: MESSAGE,
                    });
                }
            },
            UpdateExpression: (node) => {
                const updateExpression = node;
                const type = (0, type_js_1.getTypeFromTreeNode)(updateExpression.argument, services);
                if (isBooleanStringOrDate(type)) {
                    (0, location_js_1.report)(context, {
                        node: updateExpression.argument,
                        message: MESSAGE,
                    });
                }
            },
        };
    },
};
function isDateMinusDateException(leftType, rightType, operator) {
    if (operator !== '-' && operator !== '-=') {
        return false;
    }
    if (leftType.symbol?.name === 'Date' &&
        (rightType.symbol?.name === 'Date' || (rightType.flags & typescript_1.default.TypeFlags.Any) > 0)) {
        return true;
    }
    if (rightType.symbol?.name === 'Date' && (leftType.flags & typescript_1.default.TypeFlags.Any) > 0) {
        return true;
    }
    return false;
}
function checkPlus(leftType, rightType, expression, context) {
    if (isNumber(leftType) && isBooleanOrDate(rightType)) {
        (0, location_js_1.report)(context, {
            node: expression.right,
            message: MESSAGE,
        }, [(0, location_js_1.toSecondaryLocation)(expression.left)]);
    }
    if (isNumber(rightType) && isBooleanOrDate(leftType)) {
        (0, location_js_1.report)(context, {
            node: expression.left,
            message: MESSAGE,
        }, [(0, location_js_1.toSecondaryLocation)(expression.right)]);
    }
}
function checkComparison(leftType, rightType, expression, context) {
    if (isBooleanOrNumber(leftType) && isBooleanStringOrDate(rightType)) {
        (0, location_js_1.report)(context, {
            node: expression.right,
            message: MESSAGE,
        });
    }
    else if (isBooleanOrNumber(rightType) && isBooleanStringOrDate(leftType)) {
        (0, location_js_1.report)(context, {
            node: expression.left,
            message: MESSAGE,
        });
    }
}
function checkArithmetic(leftType, rightType, expression, context) {
    if (isDateMinusDateException(leftType, rightType, expression.operator)) {
        return;
    }
    const secondaryLocations = [];
    if (isBooleanStringOrDate(leftType)) {
        secondaryLocations.push((0, location_js_1.toSecondaryLocation)(expression.left));
    }
    if (isBooleanStringOrDate(rightType)) {
        secondaryLocations.push((0, location_js_1.toSecondaryLocation)(expression.right));
    }
    if (secondaryLocations.length !== 0) {
        (0, location_js_1.report)(context, {
            node: expression,
            message: 'Convert the operands of this operation into numbers.',
        }, secondaryLocations);
    }
}
function isBooleanOrDate(type) {
    if (isBoolean(type)) {
        return true;
    }
    return type.symbol?.name === 'Date';
}
function isBooleanOrNumber(type) {
    return isBoolean(type) || isNumber(type);
}
function isBoolean(type) {
    return (type.flags & typescript_1.default.TypeFlags.BooleanLike) > 0 || type.symbol?.name === 'Boolean';
}
function isNumber(type) {
    return (type.flags & typescript_1.default.TypeFlags.NumberLike) > 0 || type.symbol?.name === 'Number';
}
function isBooleanStringOrDate(type) {
    return isBoolean(type) || (0, type_js_1.isStringType)(type) || type.symbol?.name === 'Date';
}
