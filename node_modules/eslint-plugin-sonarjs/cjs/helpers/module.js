"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.isESModule = isESModule;
exports.getImportDeclarations = getImportDeclarations;
exports.getRequireCalls = getRequireCalls;
exports.isRequire = isRequire;
exports.getFullyQualifiedName = getFullyQualifiedName;
exports.removeNodePrefixIfExists = removeNodePrefixIfExists;
exports.reduceToIdentifier = reduceToIdentifier;
const ast_js_1 = require("./ast.js");
/**
 * Checks if the current file is an ES module based on sourceType.
 *
 * The parser sets sourceType based on file extension (.mjs/.cjs),
 * package.json "type" field, and ESLint configuration.
 */
function isESModule(context) {
    return context.sourceCode.ast.sourceType === 'module';
}
function getImportDeclarations(context) {
    if (isESModule(context)) {
        return context.sourceCode.ast.body.filter(node => node.type === 'ImportDeclaration');
    }
    return [];
}
function getRequireCalls(context) {
    const required = [];
    const { scopeManager } = context.sourceCode;
    for (const scope of scopeManager.scopes) {
        for (const variable of scope.variables) {
            for (const def of variable.defs) {
                if (def.type === 'Variable' && def.node.init) {
                    if (isRequire(def.node.init)) {
                        required.push(def.node.init);
                    }
                    else if (def.node.init.type === 'MemberExpression' && isRequire(def.node.init.object)) {
                        required.push(def.node.init.object);
                    }
                }
            }
        }
    }
    return required;
}
function isRequire(node) {
    return (node.type === 'CallExpression' &&
        node.callee.type === 'Identifier' &&
        node.callee.name === 'require' &&
        node.arguments.length === 1);
}
/**
 * Returns 'module' if `node` is a `require('module')` CallExpression
 *
 * For usage inside rules, prefer getFullyQualifiedName()
 *
 * @param node
 * @returns the module name or undefined
 */
function getModuleNameFromRequire(node) {
    if (isRequire(node)) {
        const moduleName = node.arguments[0];
        if (moduleName.type === 'Literal') {
            return moduleName;
        }
    }
    return undefined;
}
/**
 * Returns the fully qualified name of ESLint node
 *
 * This function filters out the `node:` prefix
 *
 * A fully qualified name here denotes a value that is accessed through an imported
 * symbol, e.g., `foo.bar.baz` where `foo` was imported either from a require call
 * or an import statement:
 *
 * ```
 * const foo = require('lib');
 * foo.bar.baz.qux; // matches the fully qualified name 'lib.bar.baz.qux' (not 'foo.bar.baz.qux')
 * const foo2 = require('lib').bar;
 * foo2.baz.qux; // matches the fully qualified name 'lib.bar.baz.qux'
 * ```
 *
 * Returns null when an FQN could not be found.
 *
 * @param context the rule context
 * @param node the node
 * @param fqn the already traversed FQN (for recursive calls)
 * @param scope scope to look for the variable definition, used in recursion not to
 *              loop over same variable always in the lower scope
 */
function getFullyQualifiedName(context, node, fqn = [], scope) {
    return removeNodePrefixIfExists(getFullyQualifiedNameRaw(context, node, fqn, scope));
}
/**
 * Just like getFullyQualifiedName(), but does not filter out the `node:` prefix.
 *
 * To be used for rules that need to work with the `node:` prefix.
 */
function getFullyQualifiedNameRaw(context, node, fqn, scope, visitedVars = []) {
    const nodeToCheck = reduceToIdentifier(node, fqn);
    if (!(0, ast_js_1.isIdentifier)(nodeToCheck)) {
        // require chaining, e.g. `require('lib')()` or `require('lib').prop()`
        if (node.type === 'CallExpression') {
            const qualifiers = [];
            const maybeRequire = reduceTo('CallExpression', node.callee, qualifiers);
            const module = getModuleNameFromRequire(maybeRequire);
            if (typeof module?.value === 'string') {
                qualifiers.unshift(module.value);
                return qualifiers.join('.');
            }
        }
        return null;
    }
    const variable = (0, ast_js_1.getVariableFromScope)(scope ?? context.sourceCode.getScope(node), nodeToCheck.name);
    if (!variable || variable.defs.length > 1) {
        return null;
    }
    // built-in variable
    // ESLint marks built-in global variables with an undocumented hidden `writeable` property that should equal `false`.
    // @see https://github.com/eslint/eslint/blob/6380c87c563be5dc78ce0ddd5c7409aaf71692bb/lib/linter/linter.js#L207
    // @see https://github.com/eslint/eslint/blob/6380c87c563be5dc78ce0ddd5c7409aaf71692bb/lib/rules/no-global-assign.js#L81
    if (variable.writeable === false || visitedVars.includes(variable)) {
        fqn.unshift(nodeToCheck.name);
        return fqn.join('.');
    }
    const definition = variable.defs.find(({ type }) => ['ImportBinding', 'Variable'].includes(type));
    if (!definition) {
        return null;
    }
    // imports
    const fqnFromImport = checkFqnFromImport(variable, definition, context, fqn, visitedVars);
    if (fqnFromImport !== null) {
        return fqnFromImport;
    }
    // requires
    const fqnFromRequire = checkFqnFromRequire(variable, definition, context, fqn, visitedVars);
    if (fqnFromRequire !== null) {
        return fqnFromRequire;
    }
    return null;
}
function checkFqnFromImport(variable, definition, context, fqn, visitedVars) {
    if (definition.type === 'ImportBinding') {
        const specifier = definition.node;
        const importDeclaration = definition.parent;
        // import {default as cdk} from 'aws-cdk-lib';
        // vs.
        // import { aws_s3 as s3 } from 'aws-cdk-lib';
        if (specifier.type === 'ImportSpecifier' &&
            specifier.imported.type === 'Identifier' &&
            specifier.imported?.name !== 'default') {
            fqn.unshift(specifier.imported?.name);
        }
        if (typeof importDeclaration.source?.value === 'string') {
            const importedQualifiers = importDeclaration.source.value.split('/');
            fqn.unshift(...importedQualifiers);
            return fqn.join('.');
        }
        // example: import s3 = require('aws-cdk-lib/aws-s3');
        if (importDeclaration.type === 'TSImportEqualsDeclaration') {
            const importedModule = importDeclaration
                .moduleReference;
            if (importedModule.type === 'TSExternalModuleReference' &&
                importedModule.expression.type === 'Literal' &&
                typeof importedModule.expression.value === 'string') {
                const importedQualifiers = importedModule.expression.value.split('/');
                fqn.unshift(...importedQualifiers);
                return fqn.join('.');
            }
            // example: import s3 = cdk.aws_s3;
            if (importedModule.type === 'TSQualifiedName') {
                visitedVars.push(variable);
                return getFullyQualifiedNameRaw(context, importedModule, fqn, variable.scope, visitedVars);
            }
        }
    }
    return null;
}
function checkFqnFromRequire(variable, definition, context, fqn, visitedVars) {
    const value = (0, ast_js_1.getUniqueWriteReference)(variable);
    // requires
    if (definition.type === 'Variable' && value) {
        // case for `const {Bucket} = require('aws-cdk-lib/aws-s3');`
        // case for `const {Bucket: foo} = require('aws-cdk-lib/aws-s3');`
        if (definition.node.id.type === 'ObjectPattern') {
            for (const property of definition.node.id.properties) {
                if (property.value === definition.name) {
                    fqn.unshift(property.key.name);
                }
            }
        }
        const nodeToCheck = reduceTo('CallExpression', value, fqn);
        const module = getModuleNameFromRequire(nodeToCheck)?.value;
        if (typeof module === 'string') {
            const importedQualifiers = module.split('/');
            fqn.unshift(...importedQualifiers);
            return fqn.join('.');
        }
        else {
            visitedVars.push(variable);
            return getFullyQualifiedNameRaw(context, nodeToCheck, fqn, variable.scope, visitedVars);
        }
    }
    return null;
}
/**
 * Removes `node:` prefix if such exists
 *
 * Node.js builtin modules can be referenced with a `node:` prefix (eg.: node:fs/promises)
 *
 * https://nodejs.org/api/esm.html#node-imports
 *
 * @param fqn Fully Qualified Name (ex.: `node:https.request`)
 * @returns `fqn` sanitized from `node:` prefix (ex.: `https.request`)
 */
function removeNodePrefixIfExists(fqn) {
    if (fqn === null) {
        return null;
    }
    const NODE_NAMESPACE = 'node:';
    if (fqn.startsWith(NODE_NAMESPACE)) {
        return fqn.substring(NODE_NAMESPACE.length);
    }
    return fqn;
}
/**
 * Helper function for getFullyQualifiedName to handle Member expressions
 * filling in the FQN array with the accessed properties.
 * @param node the Node to traverse
 * @param fqn the array with the qualifiers
 */
function reduceToIdentifier(node, fqn = []) {
    return reduceTo('Identifier', node, fqn);
}
/**
 * Reduce a given node through its ancestors until a given node type is found
 * filling in the FQN array with the accessed properties.
 * @param type the type of node you are looking for to be returned. Returned node still needs to be
 *             checked as its type it's not guaranteed to match the passed type.
 * @param node the Node to traverse
 * @param fqn the array with the qualifiers
 */
function reduceTo(type, node, fqn = []) {
    let nodeToCheck = node;
    while (nodeToCheck.type !== type) {
        if (nodeToCheck.type === 'MemberExpression') {
            const { property } = nodeToCheck;
            if (property.type === 'Literal' && typeof property.value === 'string') {
                fqn.unshift(property.value);
            }
            else if (property.type === 'Identifier') {
                fqn.unshift(property.name);
            }
            nodeToCheck = nodeToCheck.object;
        }
        else if (nodeToCheck.type === 'CallExpression' && !getModuleNameFromRequire(nodeToCheck)) {
            nodeToCheck = nodeToCheck.callee;
        }
        else if (nodeToCheck.type === 'NewExpression') {
            nodeToCheck = nodeToCheck.callee;
        }
        else if (nodeToCheck.type === 'ChainExpression') {
            nodeToCheck = nodeToCheck.expression;
        }
        else if (nodeToCheck.type === 'TSNonNullExpression') {
            // we should migrate to use only TSESTree types everywhere to avoid casting
            nodeToCheck = nodeToCheck
                .expression;
        }
        else if (nodeToCheck.type === 'TSQualifiedName') {
            const qualified = nodeToCheck;
            fqn.unshift(qualified.right.name);
            nodeToCheck = qualified.left;
        }
        else {
            break;
        }
    }
    return nodeToCheck;
}
