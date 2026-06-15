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
// https://sonarsource.github.io/rspec/#/rspec/S3972
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
const message = 'Move this "if" to a new line or add the missing "else".';
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        hasSuggestions: true,
        messages: {
            sameLineCondition: message,
            suggestAddingElse: 'Add "else" keyword',
            suggestAddingNewline: 'Move this "if" to a new line',
        },
    }),
    create(context) {
        function checkStatements(statements) {
            const { sourceCode } = context;
            const siblingIfStatements = getSiblingIfStatements(statements);
            for (const siblingIfStatement of siblingIfStatements) {
                const precedingIf = siblingIfStatement.first;
                const followingIf = siblingIfStatement.following;
                if (!!precedingIf.loc &&
                    !!followingIf.loc &&
                    precedingIf.loc.end.line === followingIf.loc.start.line &&
                    precedingIf.loc.start.line !== followingIf.loc.end.line) {
                    const precedingIfLastToken = sourceCode.getLastToken(precedingIf);
                    const followingIfToken = sourceCode.getFirstToken(followingIf);
                    (0, location_js_1.report)(context, {
                        messageId: 'sameLineCondition',
                        message,
                        loc: followingIfToken.loc,
                        suggest: [
                            {
                                messageId: 'suggestAddingElse',
                                fix: fixer => fixer.insertTextBefore(followingIfToken, 'else '),
                            },
                            {
                                messageId: 'suggestAddingNewline',
                                fix: fixer => fixer.replaceTextRange([precedingIf.range[1], followingIf.range[0]], '\n' + ' '.repeat(precedingIf.loc.start.column)),
                            },
                        ],
                    }, [(0, location_js_1.toSecondaryLocation)(precedingIfLastToken)]);
                }
            }
        }
        return {
            Program: (node) => checkStatements(node.body),
            BlockStatement: (node) => checkStatements(node.body),
            SwitchCase: (node) => checkStatements(node.consequent),
        };
    },
};
function getSiblingIfStatements(statements) {
    return statements.reduce((siblingsArray, statement, currentIndex) => {
        const previousStatement = statements[currentIndex - 1];
        if (statement.type === 'IfStatement' &&
            !!previousStatement &&
            previousStatement.type === 'IfStatement') {
            return [{ first: previousStatement, following: statement }, ...siblingsArray];
        }
        return siblingsArray;
    }, []);
}
