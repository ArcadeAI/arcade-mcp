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
// https://sonarsource.github.io/rspec/#/rspec/S5869/javascript
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
const location_js_1 = require("../helpers/location.js");
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const meta = __importStar(require("./generated-meta.js"));
const rule_template_js_1 = require("../helpers/regex/rule-template.js");
const simplified_regex_character_class_js_1 = require("../helpers/regex/simplified-regex-character-class.js");
const location_js_2 = require("../helpers/regex/location.js");
exports.rule = (0, rule_template_js_1.createRegExpRule)(context => {
    let flags;
    return {
        onRegExpLiteralEnter: (node) => {
            flags = node.flags;
        },
        onCharacterClassEnter: (node) => {
            const duplicates = new Set();
            const characterClass = new simplified_regex_character_class_js_1.SimplifiedRegexCharacterClass(flags);
            for (const element of node.elements) {
                const intersections = new simplified_regex_character_class_js_1.SimplifiedRegexCharacterClass(flags, element).findIntersections(characterClass);
                if (intersections.length > 0) {
                    for (const intersection of intersections) {
                        duplicates.add(intersection);
                    }
                    duplicates.add(element);
                }
                characterClass.add(element);
            }
            if (duplicates.size > 0) {
                const [primary, ...secondaries] = duplicates;
                const secondaryLocations = [];
                for (const secondary of secondaries) {
                    const loc = (0, location_js_2.getRegexpLocation)(context.node, secondary, context);
                    if (loc) {
                        secondaryLocations.push((0, location_js_1.toSecondaryLocation)({ loc }, 'Additional duplicate'));
                    }
                }
                context.reportRegExpNode({
                    message: 'Remove duplicates in this character class.',
                    node: context.node,
                    regexpNode: primary,
                }, secondaryLocations);
            }
        },
    };
}, (0, generate_meta_js_1.generateMeta)(meta));
