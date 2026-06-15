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
// https://sonarsource.github.io/rspec/#/rspec/S135/javascript
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
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta),
    create(context) {
        let jumpTargets = [];
        function enterScope() {
            jumpTargets.push(new JumpTarget());
        }
        function leaveScope() {
            jumpTargets.pop();
        }
        function increateNumberOfJumpsInScopes(jump, label) {
            for (const jumpTarget of [...jumpTargets].reverse()) {
                jumpTarget.jumps.push(jump);
                if (label === jumpTarget.label) {
                    break;
                }
            }
        }
        function leaveScopeAndCheckNumberOfJumps(node) {
            const jumps = jumpTargets.pop()?.jumps;
            if (jumps && jumps.length > 1) {
                const sourceCode = context.sourceCode;
                const firstToken = sourceCode.getFirstToken(node);
                (0, location_js_1.report)(context, {
                    loc: firstToken.loc,
                    message: 'Reduce the total number of "break" and "continue" statements in this loop to use one at most.',
                }, jumps.map(jmp => (0, location_js_1.toSecondaryLocation)(jmp, jmp.type === 'BreakStatement' ? '"break" statement.' : '"continue" statement.')));
            }
        }
        return {
            Program: () => {
                jumpTargets = [];
            },
            BreakStatement: (node) => {
                const breakStatement = node;
                increateNumberOfJumpsInScopes(breakStatement, breakStatement.label?.name);
            },
            ContinueStatement: (node) => {
                const continueStatement = node;
                increateNumberOfJumpsInScopes(continueStatement, continueStatement.label?.name);
            },
            SwitchStatement: enterScope,
            'SwitchStatement:exit': leaveScope,
            ForStatement: enterScope,
            'ForStatement:exit': leaveScopeAndCheckNumberOfJumps,
            ForInStatement: enterScope,
            'ForInStatement:exit': leaveScopeAndCheckNumberOfJumps,
            ForOfStatement: enterScope,
            'ForOfStatement:exit': leaveScopeAndCheckNumberOfJumps,
            WhileStatement: enterScope,
            'WhileStatement:exit': leaveScopeAndCheckNumberOfJumps,
            DoWhileStatement: enterScope,
            'DoWhileStatement:exit': leaveScopeAndCheckNumberOfJumps,
            LabeledStatement: (node) => {
                const labeledStatement = node;
                jumpTargets.push(new JumpTarget(labeledStatement.label.name));
            },
            'LabeledStatement:exit': leaveScope,
        };
    },
};
class JumpTarget {
    constructor(label) {
        this.jumps = [];
        this.label = label;
    }
}
