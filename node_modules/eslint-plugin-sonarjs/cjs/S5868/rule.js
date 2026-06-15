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
// https://sonarsource.github.io/rspec/#/rspec/S5868/javascript
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
const ancestor_js_1 = require("../helpers/ancestor.js");
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const ast_js_1 = require("../helpers/ast.js");
const regexpp_1 = require("@eslint-community/regexpp");
const meta = __importStar(require("./generated-meta.js"));
const extract_js_1 = require("../helpers/regex/extract.js");
const flags_js_1 = require("../helpers/regex/flags.js");
const rule_template_js_1 = require("../helpers/regex/rule-template.js");
const ast_js_2 = require("../helpers/regex/ast.js");
const MODIFIABLE_REGEXP_FLAGS_TYPES = new Set([
    'Literal',
    'TemplateLiteral',
    'TaggedTemplateExpression',
]);
exports.rule = (0, rule_template_js_1.createRegExpRule)(context => {
    function checkSequence(sequence) {
        // Stop on the first illegal character in the sequence
        for (let index = 0; index < sequence.length; index++) {
            if (checkCharacter(sequence[index], index, sequence)) {
                return;
            }
        }
    }
    function checkCharacter(character, index, characters) {
        // Stop on the first failed check as there may be overlaps between checks
        // for instance a zero-width-sequence containing a modified emoji.
        for (const check of characterChecks) {
            if (check(character, index, characters)) {
                return true;
            }
        }
        return false;
    }
    function checkCombinedCharacter(character, index, characters) {
        let reported = false;
        if (index !== 0 &&
            isCombiningCharacter(character.value) &&
            !isCombiningCharacter(characters[index - 1].value)) {
            const combinedChar = characters[index - 1].raw + characters[index].raw;
            const message = `Move this Unicode combined character '${combinedChar}' outside of the character class`;
            context.reportRegExpNode({ regexpNode: characters[index], node: context.node, message });
            reported = true;
        }
        return reported;
    }
    function checkSurrogatePairTailCharacter(character, index, characters) {
        let reported = false;
        if (index !== 0 && isSurrogatePair(characters[index - 1].value, character.value)) {
            const surrogatePair = characters[index - 1].raw + characters[index].raw;
            const message = `Move this Unicode surrogate pair '${surrogatePair}' outside of the character class or use 'u' flag`;
            const pattern = (0, extract_js_1.getPatternFromNode)(context.node, context)?.pattern;
            let suggest;
            if (pattern && isValidWithUnicodeFlag(pattern)) {
                suggest = [
                    {
                        desc: "Add unicode 'u' flag to regex",
                        fix: fixer => addUnicodeFlag(fixer, context.node),
                    },
                ];
            }
            context.reportRegExpNode({
                regexpNode: characters[index],
                node: context.node,
                message,
                suggest,
            });
            reported = true;
        }
        return reported;
    }
    function addUnicodeFlag(fixer, node) {
        if ((0, ast_js_1.isRegexLiteral)(node)) {
            return insertTextAfter(fixer, node, 'u');
        }
        const regExpConstructor = getRegExpConstructor(node);
        if (!regExpConstructor) {
            return null;
        }
        const args = regExpConstructor.arguments;
        if (args.length === 1) {
            const token = sourceCode.getLastToken(regExpConstructor, { skip: 1 });
            return insertTextAfter(fixer, token, ', "u"');
        }
        if (args.length > 1 && args[1]?.range && hasModifiableFlags(regExpConstructor)) {
            const [start, end] = args[1].range;
            return fixer.insertTextAfterRange([start, end - 1], 'u');
        }
        return null;
    }
    function checkModifiedEmojiCharacter(character, index, characters) {
        let reported = false;
        if (index !== 0 &&
            isEmojiModifier(character.value) &&
            !isEmojiModifier(characters[index - 1].value)) {
            const modifiedEmoji = characters[index - 1].raw + characters[index].raw;
            const message = `Move this Unicode modified Emoji '${modifiedEmoji}' outside of the character class`;
            context.reportRegExpNode({ regexpNode: characters[index], node: context.node, message });
            reported = true;
        }
        return reported;
    }
    function checkRegionalIndicatorCharacter(character, index, characters) {
        let reported = false;
        if (index !== 0 &&
            isRegionalIndicator(character.value) &&
            isRegionalIndicator(characters[index - 1].value)) {
            const regionalIndicator = characters[index - 1].raw + characters[index].raw;
            const message = `Move this Unicode regional indicator '${regionalIndicator}' outside of the character class`;
            context.reportRegExpNode({ regexpNode: characters[index], node: context.node, message });
            reported = true;
        }
        return reported;
    }
    function checkZeroWidthJoinerCharacter(character, index, characters) {
        let reported = false;
        if (index !== 0 &&
            index !== characters.length - 1 &&
            isZeroWidthJoiner(character.value) &&
            !isZeroWidthJoiner(characters[index - 1].value) &&
            !isZeroWidthJoiner(characters[index + 1].value)) {
            // It's practically difficult to determine the full joined character sequence
            // as it may join more than 2 elements that consist of characters or modified Emojis
            // see: https://unicode.org/emoji/charts/emoji-zwj-sequences.html
            const message = 'Move this Unicode joined character sequence outside of the character class';
            context.reportRegExpNode({
                regexpNode: characters[index - 1],
                node: context.node,
                message,
            });
            reported = true;
        }
        return reported;
    }
    function isValidWithUnicodeFlag(pattern) {
        try {
            validator.validatePattern(pattern, undefined, undefined, true);
            return true;
        }
        catch {
            return false;
        }
    }
    const sourceCode = context.sourceCode;
    const validator = new regexpp_1.RegExpValidator();
    // The order matters as surrogate pair check may trigger at the same time as zero-width-joiner.
    const characterChecks = [
        checkCombinedCharacter,
        checkZeroWidthJoinerCharacter,
        checkModifiedEmojiCharacter,
        checkRegionalIndicatorCharacter,
        checkSurrogatePairTailCharacter,
    ];
    return {
        onCharacterClassEnter(ccNode) {
            for (const chars of characters(ccNode.elements)) {
                checkSequence(chars);
            }
        },
    };
}, (0, generate_meta_js_1.generateMeta)(meta, { hasSuggestions: true }));
function characters(nodes) {
    let current = [];
    const sequences = [current];
    for (const node of nodes) {
        if (node.type === 'Character') {
            current.push(node);
        }
        else if (node.type === 'CharacterClassRange') {
            // for following regexp [xa-z] we produce [[xa],[z]]
            // we would report for example if instead of 'xa' there would be unicode combined class
            current.push(node.min);
            current = [node.max];
            sequences.push(current);
        }
        else if (node.type === 'CharacterSet' && current.length > 0) {
            // CharacterSet is for example [\d], ., or \p{ASCII}
            // see https://github.com/mysticatea/regexpp/blob/master/src/ast.ts#L222
            current = [];
            sequences.push(current);
        }
    }
    return sequences;
}
function isCombiningCharacter(codePoint) {
    return /^[\p{Mc}\p{Me}\p{Mn}]$/u.test(String.fromCodePoint(codePoint));
}
function isSurrogatePair(lead, tail) {
    return lead >= 0xd800 && lead < 0xdc00 && tail >= 0xdc00 && tail < 0xe000;
}
function isEmojiModifier(code) {
    return code >= 0x1f3fb && code <= 0x1f3ff;
}
function isRegionalIndicator(code) {
    return code >= 0x1f1e6 && code <= 0x1f1ff;
}
function isZeroWidthJoiner(code) {
    return code === 0x200d;
}
function getRegExpConstructor(node) {
    return (0, ancestor_js_1.ancestorsChain)(node, new Set(['CallExpression', 'NewExpression'])).find(n => (0, ast_js_2.isRegExpConstructor)(n));
}
function hasModifiableFlags(regExpConstructor) {
    const args = regExpConstructor.arguments;
    return (typeof args[1]?.range?.[0] === 'number' &&
        typeof args[1]?.range?.[1] === 'number' &&
        (0, flags_js_1.getFlags)(regExpConstructor) != null &&
        MODIFIABLE_REGEXP_FLAGS_TYPES.has(args[1].type));
}
function insertTextAfter(fixer, node, text) {
    return node ? fixer.insertTextAfter(node, text) : null;
}
