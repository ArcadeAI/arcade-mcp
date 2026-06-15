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
// https://sonarsource.github.io/rspec/#/rspec/S3626
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
const loops = 'WhileStatement, ForStatement, DoWhileStatement, ForInStatement, ForOfStatement';
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            removeRedundantJump: 'Remove this redundant jump.',
            suggestJumpRemoval: 'Remove this redundant jump',
        },
        hasSuggestions: true,
    }),
    create(context) {
        function reportIfLastStatement(node) {
            const withArgument = node.type === 'ContinueStatement' ? !!node.label : !!node.argument;
            if (!withArgument) {
                const block = node.parent;
                if (block.body.at(-1) === node && block.body.length > 1) {
                    const previousComments = context.sourceCode.getCommentsBefore(node);
                    const previousToken = previousComments.length === 0
                        ? context.sourceCode.getTokenBefore(node)
                        : (0, collection_js_1.last)(previousComments);
                    context.report({
                        messageId: 'removeRedundantJump',
                        node: node,
                        suggest: [
                            {
                                messageId: 'suggestJumpRemoval',
                                fix: fixer => fixer.removeRange([previousToken.range[1], node.range[1]]),
                            },
                        ],
                    });
                }
            }
        }
        function reportIfLastStatementInsideIf(node) {
            const ancestors = context.sourceCode.getAncestors(node);
            const ifStatement = ancestors.at(-2);
            const upperBlock = ancestors.at(-3);
            if (upperBlock.body.at(-1) === ifStatement) {
                reportIfLastStatement(node);
            }
        }
        return {
            [`:matches(${loops}) > BlockStatement > ContinueStatement`]: (node) => {
                reportIfLastStatement(node);
            },
            [`:matches(${loops}) > BlockStatement > IfStatement > BlockStatement > ContinueStatement`]: (node) => {
                reportIfLastStatementInsideIf(node);
            },
            ':function > BlockStatement > ReturnStatement': (node) => {
                reportIfLastStatement(node);
            },
            ':function > BlockStatement > IfStatement > BlockStatement > ReturnStatement': (node) => {
                reportIfLastStatementInsideIf(node);
            },
        };
    },
};
