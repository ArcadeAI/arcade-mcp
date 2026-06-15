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
// https://sonarsource.github.io/rspec/#/rspec/S6324/javascript
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
const rule_template_js_1 = require("../helpers/regex/rule-template.js");
const EXCEPTIONS = new Set(['\t', '\n']);
const MAX_CONTROL_CHAR_CODE = 0x1f;
// ANSI escape sequence control characters
const ESC = 0x1b;
const BEL = 0x07;
const LEFT_BRACKET = 0x5b; // [
const RIGHT_BRACKET = 0x5d; // ]
/**
 * Control characters used as range boundaries (e.g., [\x00-\x1f]) indicate intentional usage.
 */
function isCharacterClassRangeBoundary(character) {
    return character.parent.type === 'CharacterClassRange';
}
/**
 * Control characters inside character classes that contain ranges indicate intentional
 * character set construction (e.g., [\x00-\x08\x0b\x0c] for YAML/CSS non-printables).
 */
function isInCharacterClassWithRanges(character) {
    const parent = character.parent;
    if (parent.type !== 'CharacterClass') {
        return false;
    }
    return parent.elements.some(element => element.type === 'CharacterClassRange');
}
/**
 * Checks if ESC (0x1b) is followed by [ or ] to form ANSI CSI/OSC sequence start.
 * Per xterm spec, ESC + [ starts a CSI sequence, ESC + ] starts an OSC sequence.
 */
function isAnsiSequenceStart(character) {
    if (character.value !== ESC) {
        return false;
    }
    const parent = character.parent;
    if (parent.type !== 'Alternative') {
        return false;
    }
    const elements = parent.elements;
    const index = elements.indexOf(character);
    if (index === -1 || index >= elements.length - 1) {
        return false;
    }
    const next = elements[index + 1];
    if (next.type !== 'Character') {
        return false;
    }
    return next.value === LEFT_BRACKET || next.value === RIGHT_BRACKET;
}
/**
 * Checks if BEL (0x07) is used as OSC sequence terminator.
 * Per xterm spec, BEL is valid only as an OSC terminator (after ESC + ]).
 * It should NOT be exempted after CSI sequences (ESC + [).
 */
function isOscTerminator(character) {
    if (character.value !== BEL) {
        return false;
    }
    const parent = character.parent;
    if (parent.type !== 'Alternative') {
        return false;
    }
    const elements = parent.elements;
    // Look backwards for ESC + ] pattern indicating OSC sequence start
    for (let i = elements.indexOf(character) - 1; i >= 1; i--) {
        const curr = elements[i];
        const prev = elements[i - 1];
        if (curr.type === 'Character' &&
            curr.value === RIGHT_BRACKET &&
            prev.type === 'Character' &&
            prev.value === ESC) {
            return true;
        }
    }
    return false;
}
exports.rule = (0, rule_template_js_1.createRegExpRule)(context => {
    return {
        onCharacterEnter: (character) => {
            const { value, raw } = character;
            if (value >= 0x00 &&
                value <= MAX_CONTROL_CHAR_CODE &&
                (isSameInterpreted(raw, value) ||
                    raw.startsWith(String.raw `\x`) ||
                    raw.startsWith(String.raw `\u`)) &&
                !EXCEPTIONS.has(raw) &&
                !isCharacterClassRangeBoundary(character) &&
                !isInCharacterClassWithRanges(character) &&
                !isAnsiSequenceStart(character) &&
                !isOscTerminator(character)) {
                context.reportRegExpNode({
                    message: 'Remove this control character.',
                    node: context.node,
                    regexpNode: character,
                });
            }
        },
    };
}, (0, generate_meta_js_1.generateMeta)(meta));
/**
 * When the character has been interpreted, we need to compare its
 * code point value.
 */
function isSameInterpreted(raw, value) {
    return raw.codePointAt(0) === value;
}
