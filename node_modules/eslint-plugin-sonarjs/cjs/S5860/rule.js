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
// https://sonarsource.github.io/rspec/#/rspec/S5860/javascript
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
const regexpp = __importStar(require("@eslint-community/regexpp"));
const location_js_1 = require("../helpers/location.js");
const parser_services_js_1 = require("../helpers/parser-services.js");
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const ast_js_1 = require("../helpers/ast.js");
const type_js_1 = require("../helpers/type.js");
const meta = __importStar(require("./generated-meta.js"));
const ast_js_2 = require("../helpers/regex/ast.js");
const group_js_1 = require("../helpers/regex/group.js");
const location_js_2 = require("../helpers/regex/location.js");
const extract_js_1 = require("../helpers/regex/extract.js");
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta),
    create(context) {
        const services = context.sourceCode.parserServices;
        if (!(0, parser_services_js_1.isRequiredParserServices)(services)) {
            return {};
        }
        const intellisense = new RegexIntelliSense(services, context);
        return {
            'Literal[regex]:exit': (literal) => {
                /* /regex/ */
                intellisense.collectKnowledge(literal);
            },
            'NewExpression:exit': (newExpr) => {
                /* new RegExp(regex) */
                intellisense.collectKnowledge(newExpr);
            },
            'CallExpression:exit': (callExpr) => {
                /* RegExp(regex), implicit regex e.g. str.match('regex') */
                intellisense.collectKnowledge(callExpr);
                /* str.match(pattern) / pattern.exec(str) */
                intellisense.collectPatternMatcher(callExpr);
                /* str.replace(pattern, substr) */
                checkStringReplaceGroupReferences(callExpr, intellisense);
            },
            'MemberExpression:exit': (memberExpr) => {
                if (memberExpr.computed) {
                    /* matcher[index] */
                    checkIndexBasedGroupReference(memberExpr, intellisense);
                }
                else {
                    /* matcher.groups.<name> / matcher.indices.groups.<name> */
                    checkNonExistingGroupReference(memberExpr, intellisense);
                }
            },
            'Program:exit': () => {
                checkUnusedGroups(intellisense);
                checkIndexedGroups(intellisense);
            },
        };
    },
};
function checkStringReplaceGroupReferences(callExpr, intellisense) {
    if ((0, ast_js_2.isStringReplaceCall)(callExpr, intellisense.services)) {
        const [pattern, substr] = callExpr.arguments;
        const regex = intellisense.findRegex(pattern);
        if (regex) {
            const references = (0, group_js_1.extractReferences)(substr);
            const indexes = new Set();
            const names = new Set();
            for (const ref of references) {
                Number.isNaN(Number(ref.value)) ? names.add(ref.value) : indexes.add(Number(ref.value));
            }
            for (const group of regex.groups) {
                group.used ||= names.has(group.name);
                group.used ||= indexes.has(group.index);
            }
            const indexedGroups = regex.groups.filter(group => indexes.has(group.index));
            if (indexedGroups.length > 0) {
                const locations = prepareSecondaries(regex, indexedGroups, intellisense, 'Group');
                (0, location_js_1.report)(intellisense.context, {
                    message: `Directly use the group names instead of their numbers.`,
                    node: substr,
                }, locations);
            }
        }
    }
}
function checkIndexBasedGroupReference(memberExpr, intellisense) {
    const { object: matcher, property } = memberExpr;
    const regex = intellisense.resolve(matcher);
    if (regex) {
        const maybeIndex = (0, ast_js_1.getValueOfExpression)(intellisense.context, property, 'Literal');
        if (maybeIndex && typeof maybeIndex.value === 'number') {
            const index = maybeIndex.value;
            const group = regex.groups.find(grp => grp.index === index);
            if (group) {
                group.used = true;
                const locations = prepareSecondaries(regex, [group], intellisense, 'Group');
                (0, location_js_1.report)(intellisense.context, {
                    message: `Directly use '${group.name}' instead of its group number.`,
                    node: property,
                }, locations);
            }
        }
    }
}
function checkNonExistingGroupReference(memberExpr, intellisense) {
    const { object: matcher } = memberExpr;
    const regex = intellisense.resolve(matcher);
    if (regex) {
        /* matcher.groups.<name> / matcher.indices.groups.<name>  */
        const groupNodes = extractGroupNodes(memberExpr, intellisense);
        for (const groupNode of groupNodes) {
            const groupName = groupNode.type === 'Identifier' ? groupNode.name : groupNode.value;
            const group = regex.groups.find(grp => grp.name === groupName);
            if (group) {
                group.used = true;
            }
            else {
                const locations = prepareSecondaries(regex, regex.groups, intellisense, 'Named group');
                (0, location_js_1.report)(intellisense.context, {
                    message: `There is no group named '${groupName}' in the regular expression.`,
                    node: groupNode,
                }, locations);
            }
        }
    }
}
function extractGroupNodes(memberExpr, intellisense) {
    if ((0, ast_js_1.isDotNotation)(memberExpr)) {
        const { property } = memberExpr;
        const ancestors = intellisense.context.sourceCode.getAncestors(memberExpr);
        let parent = ancestors.pop();
        while (parent.type === 'TSNonNullExpression') {
            parent = ancestors.pop();
        }
        if (parent) {
            switch (property.name) {
                case 'groups':
                    /* matcher.groups.<name> or matcher.groups['name'] */
                    return extractNamedOrDestructuredGroupNodes(parent);
                case 'indices':
                    /* matcher.indices.groups.<name> or matcher.indices.groups['name'] */
                    if ((0, ast_js_1.isDotNotation)(parent) && parent.property.name === 'groups') {
                        parent = ancestors.pop();
                        if (parent) {
                            return extractNamedOrDestructuredGroupNodes(parent);
                        }
                    }
            }
        }
    }
    return [];
}
function extractNamedOrDestructuredGroupNodes(node) {
    if ((0, ast_js_1.isDotNotation)(node) || (0, ast_js_1.isIndexNotation)(node)) {
        /* matcher.groups.<name> or matcher.groups['name'] */
        return [node.property];
    }
    else if ((0, ast_js_1.isObjectDestructuring)(node)) {
        /* { <name1>,..<nameN> } = matcher.groups */
        const destructuredGroups = [];
        const pattern = node.type === 'VariableDeclarator' ? node.id : node.left;
        for (const property of pattern.properties) {
            if (property.type === 'Property' && property.key.type === 'Identifier') {
                destructuredGroups.push(property.key);
            }
        }
        return destructuredGroups;
    }
    else {
        return [];
    }
}
function checkUnusedGroups(intellisense) {
    for (const regex of intellisense.getKnowledge()) {
        if (regex.matched) {
            const unusedGroups = regex.groups.filter(group => !group.used);
            if (unusedGroups.length) {
                const locations = prepareSecondaries(regex, unusedGroups, intellisense, 'Named group');
                (0, location_js_1.report)(intellisense.context, {
                    message: 'Use the named groups of this regex or remove the names.',
                    node: regex.node,
                }, locations);
            }
        }
    }
}
function prepareSecondaries(regex, groups, intellisense, label) {
    const locations = [];
    for (const grp of groups) {
        const loc = (0, location_js_2.getRegexpLocation)(regex.node, grp.node, intellisense.context);
        if (loc) {
            locations.push((0, location_js_1.toSecondaryLocation)({ loc }, `${label} '${grp.name}'`));
        }
    }
    return locations;
}
function checkIndexedGroups(intellisense) {
    for (const regex of intellisense.getKnowledge()) {
        for (const group of regex.groups) {
            const locations = prepareSecondaries(regex, [group], intellisense, 'Group');
            for (const reference of group.node.references) {
                const loc = (0, location_js_2.getRegexpLocation)(regex.node, reference, intellisense.context);
                if (loc && typeof reference.ref === 'number') {
                    (0, location_js_1.report)(intellisense.context, {
                        message: `Directly use '${group.name}' instead of its group number.`,
                        loc,
                    }, locations);
                }
            }
        }
    }
}
function isAmbiguousGroup(reference) {
    return reference.ambiguous;
}
function makeRegexKnowledge(node, regexp) {
    const capturingGroups = [];
    const backreferences = [];
    regexpp.visitRegExpAST(regexp, {
        onBackreferenceEnter: reference => {
            const shouldSaveReference = isAmbiguousGroup(reference)
                ? reference.resolved.some(capturingGroup => capturingGroup.name)
                : reference.resolved.name !== null;
            if (shouldSaveReference) {
                backreferences.push(reference);
            }
        },
        onCapturingGroupEnter: group => capturingGroups.push(group),
    });
    const groups = [];
    for (const [index, group] of capturingGroups.entries()) {
        group.name && groups.push(makeGroupKnowledge(group, backreferences, index + 1));
    }
    return { node, regexp, groups, matched: false };
}
function makeGroupKnowledge(node, backreferences, index) {
    const name = node.name;
    const used = backreferences.some(backreference => backreference.ambiguous
        ? backreference.resolved.includes(node)
        : backreference.resolved === node);
    return { node, name, used, index };
}
class RegexIntelliSense {
    constructor(services, context) {
        this.services = services;
        this.context = context;
        this.knowledge = [];
        this.bindings = new Map();
    }
    getKnowledge() {
        return this.knowledge;
    }
    collectKnowledge(node) {
        let regexNode = node;
        if (node.type === 'CallExpression' && (0, ast_js_2.isStringRegexMethodCall)(node, this.services)) {
            /* implicit regex */
            regexNode = node.arguments[0];
        }
        const regex = (0, extract_js_1.getParsedRegex)(regexNode, this.context);
        if (regex !== null) {
            this.knowledge.push(makeRegexKnowledge(regexNode, regex));
        }
    }
    collectPatternMatcher(callExpr) {
        const { callee, arguments: args } = callExpr;
        if ((0, ast_js_1.isMethodCall)(callExpr) && args.length > 0) {
            const target = callee.object;
            const matcher = (0, ast_js_1.getLhsVariable)(this.context, callExpr);
            if (matcher) {
                const method = callee.property;
                if ((0, type_js_1.isString)(target, this.services) && ['match', 'matchAll'].includes(method.name)) {
                    /* str.match(pattern) */
                    const [pattern] = args;
                    this.bind(pattern, matcher);
                }
                else if (method.name === 'exec' && (0, type_js_1.isString)(args[0], this.services)) {
                    /* pattern.exec(str) */
                    const pattern = target;
                    this.bind(pattern, matcher);
                }
            }
        }
    }
    resolve(matcher) {
        const variable = this.findVariable(matcher);
        if (variable) {
            return this.bindings.get(variable) ?? null;
        }
        else {
            return null;
        }
    }
    findRegex(node) {
        return this.findRegexRec(node, new Set());
    }
    findRegexRec(node, visited) {
        if (!visited.has(node)) {
            visited.add(node);
            const variable = this.findVariable(node);
            if (variable) {
                const value = (0, ast_js_1.getUniqueWriteUsage)(this.context, variable.name, node);
                if (value) {
                    const regex = this.findRegexRec(value, visited);
                    if (regex) {
                        return regex;
                    }
                }
            }
        }
        return this.knowledge.find(regex => regex.node === node);
    }
    bind(pattern, matcher) {
        const regex = this.findRegex(pattern);
        if (regex) {
            regex.matched = true;
            this.bindings.set(matcher, regex);
        }
    }
    findVariable(node) {
        if (node.type === 'Identifier') {
            return (0, ast_js_1.getVariableFromName)(this.context, node.name, node);
        }
        return null;
    }
}
