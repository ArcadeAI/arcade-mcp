"use strict";
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
const vue_js_1 = require("../helpers/vue.js");
const location_js_1 = require("../helpers/location.js");
const meta = __importStar(require("./generated-meta.js"));
// https://vuejs.org/api/sfc-script-setup.html#defineprops-defineemits
const vueMacroNames = new Set([
    'defineProps',
    'defineEmits',
    'defineExpose',
    'defineOptions',
    'defineSlots',
    'withDefaults',
]);
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta),
    create(context) {
        const excludedNames = new Set();
        const undeclaredIdentifiersByName = new Map();
        return {
            'Program:exit'(node) {
                excludedNames.clear();
                undeclaredIdentifiersByName.clear();
                const globalScope = context.sourceCode.getScope(node);
                for (const ref of globalScope.through) {
                    const identifier = ref.identifier;
                    if (excludedNames.has(identifier.name)) {
                        continue;
                    }
                    if (ref.writeExpr ||
                        hasTypeOfOperator(identifier) ||
                        isWithinWithStatement(identifier)) {
                        excludedNames.add(identifier.name);
                        continue;
                    }
                    if (vueMacroNames.has(identifier.name) && (0, vue_js_1.isInsideVueSetupScript)(identifier, context)) {
                        continue;
                    }
                    const undeclaredIndentifiers = undeclaredIdentifiersByName.get(identifier.name);
                    if (undeclaredIndentifiers) {
                        undeclaredIndentifiers.push(identifier);
                    }
                    else {
                        undeclaredIdentifiersByName.set(identifier.name, [identifier]);
                    }
                }
                for (const [name, identifiers] of undeclaredIdentifiersByName.entries()) {
                    (0, location_js_1.report)(context, {
                        node: identifiers[0],
                        message: `"${name}" does not exist. Change its name or declare it so that its usage doesn't result in a "ReferenceError".`,
                    }, identifiers.slice(1).map(node => (0, location_js_1.toSecondaryLocation)(node)));
                }
            },
        };
    },
};
function isWithinWithStatement(node) {
    return !!(0, ancestor_js_1.findFirstMatchingAncestor)(node, ancestor => ancestor.type === 'WithStatement');
}
function hasTypeOfOperator(node) {
    const parent = node.parent;
    return parent?.type === 'UnaryExpression' && parent.operator === 'typeof';
}
