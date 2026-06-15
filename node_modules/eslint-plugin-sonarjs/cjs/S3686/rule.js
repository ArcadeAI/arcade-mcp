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
// https://sonarsource.github.io/rspec/#/rspec/S3686/javascript
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
const ast_js_1 = require("../helpers/ast.js");
const location_js_1 = require("../helpers/location.js");
const meta = __importStar(require("./generated-meta.js"));
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta),
    create(context) {
        const usedInNew = new Map();
        const usedInCall = new Map();
        const hasIssue = [];
        return {
            NewExpression: (node) => {
                checkExpression(node, usedInNew, usedInCall, hasIssue, 'out', context);
            },
            CallExpression: (node) => {
                checkExpression(node, usedInCall, usedInNew, hasIssue, '', context);
            },
        };
    },
};
function checkExpression(callExpression, thisTypeUsageMap, otherTypeUsageMap, hasIssue, tail, context) {
    const variable = getVariable(callExpression, context);
    if (variable && variable.defs.length !== 0) {
        const otherTypeUsage = otherTypeUsageMap.get(variable);
        if (otherTypeUsage?.loc && !hasIssue.includes(variable)) {
            const message = `Correct the use of this function; ` +
                `on line ${otherTypeUsage.loc.start.line} it was called with${tail} "new".`;
            (0, location_js_1.report)(context, {
                node: callExpression.callee,
                message,
            }, [(0, location_js_1.toSecondaryLocation)(otherTypeUsage.callee)]);
            hasIssue.push(variable);
        }
        else {
            thisTypeUsageMap.set(variable, callExpression);
        }
    }
}
function getVariable(node, context) {
    if (node.callee.type === 'Identifier') {
        return (0, ast_js_1.getVariableFromName)(context, node.callee.name, node);
    }
    return undefined;
}
