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
// https://sonarsource.github.io/rspec/#/rspec/S6328/javascript
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
const regexpp_1 = require("@eslint-community/regexpp");
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const parser_services_js_1 = require("../helpers/parser-services.js");
const meta = __importStar(require("./generated-meta.js"));
const group_js_1 = require("../helpers/regex/group.js");
const extract_js_1 = require("../helpers/regex/extract.js");
const ast_js_1 = require("../helpers/regex/ast.js");
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            nonExistingGroup: 'Referencing non-existing group{{groups}}.',
        },
    }),
    create(context) {
        const services = context.sourceCode.parserServices;
        if (!(0, parser_services_js_1.isRequiredParserServices)(services)) {
            return {};
        }
        return {
            CallExpression: (call) => {
                if ((0, ast_js_1.isStringReplaceCall)(call, services)) {
                    const [pattern, substr] = call.arguments;
                    const regex = (0, extract_js_1.getParsedRegex)(pattern, context);
                    if (regex !== null) {
                        const groups = extractGroups(regex);
                        const references = (0, group_js_1.extractReferences)(substr);
                        const invalidReferences = references.filter(ref => !isReferencingExistingGroup(ref, groups));
                        if (invalidReferences.length > 0) {
                            const groups = `${invalidReferences.length > 1 ? 's' : ''}: ${invalidReferences
                                .map(ref => ref.raw)
                                .join(', ')}`;
                            context.report({
                                node: substr,
                                messageId: 'nonExistingGroup',
                                data: {
                                    groups,
                                },
                            });
                        }
                    }
                }
            },
        };
    },
};
class CapturingGroups {
    constructor() {
        this.names = new Set();
        this.groups = 0;
    }
    add(name) {
        if (name !== null) {
            this.names.add(name);
        }
        this.groups++;
    }
    has(name) {
        return this.names.has(name);
    }
    count() {
        return this.groups;
    }
}
function extractGroups(regex) {
    const groups = new CapturingGroups();
    (0, regexpp_1.visitRegExpAST)(regex, {
        onCapturingGroupEnter: group => groups.add(group.name),
    });
    return groups;
}
function isReferencingExistingGroup(reference, groups) {
    if (Number.isNaN(Number(reference.value))) {
        const name = reference.value;
        return groups.has(name);
    }
    else {
        const index = Number(reference.value);
        return index >= 1 && index <= groups.count();
    }
}
