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
// https://sonarsource.github.io/rspec/#/rspec/S6092/javascript
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
const chai_js_1 = require("../helpers/chai.js");
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const ast_js_1 = require("../helpers/ast.js");
const meta = __importStar(require("./generated-meta.js"));
const message = 'Refactor this uncertain assertion; it can succeed for multiple reasons.';
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta),
    create(context) {
        if (!(0, chai_js_1.isImported)(context)) {
            return {};
        }
        return {
            ExpressionStatement: (node) => {
                const elements = retrieveAssertionChainElements(node.expression);
                if (elements.length > 1 &&
                    ((0, ast_js_1.isIdentifier)(elements[0].identifier, 'expect') ||
                        getElementIndex(elements, 'should') >= 0)) {
                    checkNotThrow(context, elements);
                    checkNotInclude(context, elements);
                    checkNotHaveProperty(context, elements);
                    checkNotHaveOwnPropertyDescriptor(context, elements);
                    checkNotHaveMembers(context, elements);
                    checkChangeBy(context, elements);
                    checkNotIncDec(context, elements);
                    checkNotBy(context, elements);
                    checkNotFinite(context, elements);
                }
            },
        };
    },
};
function checkNotThrow(context, elements) {
    checkWithCondition(context, elements, 'not', 'throw', args => !!args && args.length > 0);
}
function checkNotInclude(context, elements) {
    checkWithCondition(context, elements, 'not', 'include', args => !!args && args.length > 0 && args[0].type === 'ObjectExpression');
}
function checkNotHaveProperty(context, elements) {
    checkWithCondition(context, elements, 'not', 'property', args => !!args && args.length > 1);
}
function checkNotHaveOwnPropertyDescriptor(context, elements) {
    checkWithCondition(context, elements, 'not', 'ownPropertyDescriptor', args => !!args && args.length > 1);
}
function checkNotHaveMembers(context, elements) {
    checkWithCondition(context, elements, 'not', 'members');
}
function checkChangeBy(context, elements) {
    checkWithCondition(context, elements, 'change', 'by');
}
function checkNotIncDec(context, elements) {
    checkWithCondition(context, elements, 'not', 'increase');
    checkWithCondition(context, elements, 'not', 'decrease');
}
function checkNotBy(context, elements) {
    checkWithCondition(context, elements, 'not', 'by');
}
function checkNotFinite(context, elements) {
    checkWithCondition(context, elements, 'not', 'finite');
}
function checkWithCondition(context, elements, first, second, condition = () => true) {
    const firstIndex = getElementIndex(elements, first);
    const firstElement = elements[firstIndex];
    const secondIndex = getElementIndex(elements, second);
    const secondElement = elements[secondIndex];
    if (firstElement &&
        secondElement &&
        neighborIndexes(firstIndex, secondIndex, elements) &&
        condition(secondElement.arguments)) {
        context.report({
            message,
            loc: locFromTwoNodes(firstElement.identifier, secondElement.identifier),
        });
    }
}
// first element is not applied to second if between them function call (e.g. fist.foo().second())
function neighborIndexes(firstIndex, secondIndex, elements) {
    if (firstIndex === secondIndex - 2) {
        return !elements[firstIndex + 1].arguments;
    }
    return firstIndex === secondIndex - 1;
}
function retrieveAssertionChainElements(node) {
    let currentNode = node;
    const result = [];
    let currentArguments = undefined;
    while (true) {
        if ((0, ast_js_1.isDotNotation)(currentNode)) {
            result.push({ identifier: currentNode.property, arguments: currentArguments });
            currentNode = currentNode.object;
            currentArguments = undefined;
        }
        else if (currentNode.type === 'CallExpression') {
            currentArguments = currentNode.arguments;
            currentNode = currentNode.callee;
        }
        else if ((0, ast_js_1.isIdentifier)(currentNode)) {
            result.push({ identifier: currentNode, arguments: currentArguments });
            break;
        }
        else {
            break;
        }
    }
    return result.reverse();
}
function getElementIndex(elements, name) {
    return elements.findIndex(element => (0, ast_js_1.isIdentifier)(element.identifier, name));
}
function locFromTwoNodes(start, end) {
    return {
        start: start.loc.start,
        end: end.loc.end,
    };
}
