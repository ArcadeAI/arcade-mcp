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
// https://sonarsource.github.io/rspec/#/rspec/S3973/javascript
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
const ancestor_js_1 = require("../helpers/ancestor.js");
const location_js_1 = require("../helpers/location.js");
const meta = __importStar(require("./generated-meta.js"));
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta),
    create(context) {
        const sourceCode = context.sourceCode;
        return {
            IfStatement: (node) => {
                const ifStatement = node;
                const parent = (0, ancestor_js_1.getParent)(context, node);
                if (parent && parent.type !== 'IfStatement') {
                    const firstToken = sourceCode.getFirstToken(node);
                    checkIndentation(firstToken, ifStatement.consequent, context);
                }
                if (ifStatement.alternate) {
                    const elseToken = sourceCode.getTokenBefore(ifStatement.alternate, token => token.type === 'Keyword' && token.value === 'else');
                    const alternate = ifStatement.alternate;
                    if (alternate.type === 'IfStatement') {
                        //case with "else if", we have to check the consequent of the next if
                        checkIndentation(elseToken, alternate.consequent, context);
                    }
                    else {
                        checkIndentation(getPrecedingBrace(elseToken, sourceCode) ?? elseToken, alternate, context, elseToken);
                    }
                }
            },
            'WhileStatement, ForStatement, ForInStatement, ForOfStatement': (node) => {
                const firstToken = sourceCode.getFirstToken(node);
                checkIndentation(firstToken, node.body, context);
            },
        };
    },
};
function checkIndentation(firstToken, statement, context, tokenToReport = firstToken) {
    if (firstToken && tokenToReport && statement.type !== 'BlockStatement') {
        const firstStatementToken = context.sourceCode.getFirstToken(statement);
        if (firstStatementToken &&
            firstToken.loc.start.column >= firstStatementToken.loc.start.column) {
            const message = `Use curly braces or indentation to denote the code conditionally ` +
                `executed by this "${tokenToReport.value}".`;
            (0, location_js_1.report)(context, {
                message,
                loc: tokenToReport.loc,
            }, [(0, location_js_1.toSecondaryLocation)(firstStatementToken)]);
        }
    }
}
function getPrecedingBrace(elseToken, sourceCode) {
    if (elseToken) {
        const tokenBeforeElse = sourceCode.getTokenBefore(elseToken);
        if (tokenBeforeElse?.value === '}' &&
            tokenBeforeElse.loc.start.line === elseToken.loc.start.line) {
            return tokenBeforeElse;
        }
    }
    return undefined;
}
