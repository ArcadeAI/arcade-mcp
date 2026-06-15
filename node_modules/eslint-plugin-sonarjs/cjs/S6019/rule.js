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
// https://sonarsource.github.io/rspec/#/rspec/S6019/javascript
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
const collection_js_1 = require("../helpers/collection.js");
const meta = __importStar(require("./generated-meta.js"));
const rule_template_js_1 = require("../helpers/regex/rule-template.js");
exports.rule = (0, rule_template_js_1.createRegExpRule)(context => {
    return {
        onRegExpLiteralEnter: (node) => {
            for (const { elements } of node.pattern.alternatives) {
                checkElements(elements, context);
            }
        },
    };
}, (0, generate_meta_js_1.generateMeta)(meta));
function report(quantifier, context) {
    const ending = quantifier.min === 1 ? '' : 's';
    const message = `Fix this reluctant quantifier that will only ever match ${quantifier.min} repetition${ending}.`;
    context.reportRegExpNode({
        message,
        regexpNode: quantifier,
        node: context.node,
    });
}
function checkElements(elements, context) {
    if (elements.length === 0) {
        return;
    }
    const lastElement = (0, collection_js_1.last)(elements);
    if (lastElement.type === 'Quantifier' && !lastElement.greedy) {
        report(lastElement, context);
        return;
    }
    if (elements.length === 1) {
        return;
    }
    const lastButOneElement = elements.at(-2);
    if (lastButOneElement.type === 'Quantifier' && !lastButOneElement.greedy) {
        if (lastElement.type === 'Assertion' && lastElement.kind === 'end') {
            context.reportRegExpNode({
                message: `Remove the '?' from this unnecessarily reluctant quantifier.`,
                regexpNode: lastButOneElement,
                node: context.node,
            });
        }
        else if (lastElement.type === 'Quantifier' && lastElement.min === 0) {
            report(lastButOneElement, context);
        }
    }
}
