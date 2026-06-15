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
// https://sonarsource.github.io/rspec/#/rspec/S1472/javascript
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
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            moveArguments: 'Make those call arguments start on line {{line}}.',
            moveTemplateLiteral: 'Make this template literal start on line {{line}}.',
        },
    }),
    create(context) {
        const sourceCode = context.sourceCode;
        return {
            CallExpression: (node) => {
                const call = node;
                if (call.callee.type !== 'CallExpression' && call.arguments.length === 1) {
                    const callee = getCallee(call);
                    const parenthesis = sourceCode.getLastTokenBetween(callee, call.arguments[0], isClosingParen);
                    const calleeLastLine = (parenthesis ?? sourceCode.getLastToken(callee)).loc.end.line;
                    const { start } = sourceCode.getTokenAfter(callee, isNotClosingParen).loc;
                    if (calleeLastLine !== start.line) {
                        const { end } = sourceCode.getLastToken(call).loc;
                        if (end.line === start.line) {
                            reportIssue('moveArguments', { start, end }, calleeLastLine, context);
                        }
                        else {
                            //If arguments span multiple lines, we only report the first one
                            reportIssue('moveArguments', start, calleeLastLine, context);
                        }
                    }
                }
            },
            TaggedTemplateExpression(node) {
                const { quasi } = node;
                const tokenBefore = sourceCode.getTokenBefore(quasi);
                if (tokenBefore && quasi.loc && tokenBefore.loc.end.line !== quasi.loc.start.line) {
                    const loc = {
                        start: quasi.loc.start,
                        end: {
                            line: quasi.loc.start.line,
                            column: quasi.loc.start.column + 1,
                        },
                    };
                    reportIssue('moveTemplateLiteral', loc, tokenBefore.loc.start.line, context);
                }
            },
        };
    },
};
function getCallee(call) {
    const node = call;
    return (node.typeArguments ?? node.callee);
}
function isClosingParen(token) {
    return token.type === 'Punctuator' && token.value === ')';
}
function isNotClosingParen(token) {
    return !isClosingParen(token);
}
function reportIssue(messageId, loc, line, context) {
    context.report({
        messageId,
        data: {
            line: line.toString(),
        },
        loc,
    });
}
