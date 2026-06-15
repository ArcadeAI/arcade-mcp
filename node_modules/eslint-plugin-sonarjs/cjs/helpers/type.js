"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.UTILITY_TYPES = void 0;
exports.isArray = isArray;
exports.isTypedArray = isTypedArray;
exports.isString = isString;
exports.isNumber = isNumber;
exports.isBigIntType = isBigIntType;
exports.isNumberType = isNumberType;
exports.isStringType = isStringType;
exports.isFunction = isFunction;
exports.isUnion = isUnion;
exports.isUndefinedOrNull = isUndefinedOrNull;
exports.isThenable = isThenable;
exports.isThenableOrVoidUnion = isThenableOrVoidUnion;
exports.isAny = isAny;
exports.isGenericType = isGenericType;
exports.getTypeFromTreeNode = getTypeFromTreeNode;
exports.getTypeAsString = getTypeAsString;
exports.getSymbolAtLocation = getSymbolAtLocation;
exports.getSignatureFromCallee = getSignatureFromCallee;
exports.isArrayLikeType = isArrayLikeType;
exports.isStringArray = isStringArray;
exports.isNumberArray = isNumberArray;
exports.isBigIntArray = isBigIntArray;
exports.isTypeAlias = isTypeAlias;
exports.isBooleanTrueType = isBooleanTrueType;
exports.isBooleanType = isBooleanType;
exports.isNullOrUndefinedType = isNullOrUndefinedType;
exports.isObjectType = isObjectType;
exports.typeHasMethod = typeHasMethod;
exports.isIterable = isIterable;
exports.getFunctionParameterCount = getFunctionParameterCount;
const typescript_1 = __importDefault(require("typescript"));
const ast_js_1 = require("./ast.js");
function isArray(node, services) {
    const type = getTypeFromTreeNode(node, services);
    return type.symbol?.name === 'Array';
}
/**
 * TypeScript provides a set of utility types to facilitate type transformations.
 * @see https://www.typescriptlang.org/docs/handbook/utility-types.html
 */
exports.UTILITY_TYPES = new Set([
    'Awaited',
    'Partial',
    'Required',
    'Readonly',
    'Record',
    'Pick',
    'Omit',
    'Exclude',
    'Extract',
    'NonNullable',
    'Parameters',
    'ConstructorParameters',
    'ReturnType',
    'InstanceType',
    'ThisParameterType',
    'OmitThisParameter',
    'ThisType',
    'Uppercase',
    'Lowercase',
    'Capitalize',
    'Uncapitalize',
]);
/**
 * JavaScript typed arrays
 * https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Typed_arrays
 */
const TYPED_ARRAY_TYPES = new Set([
    'Int8Array',
    'Uint8Array',
    'Uint8ClampedArray',
    'Int16Array',
    'Uint16Array',
    'Int32Array',
    'Uint32Array',
    'Float32Array',
    'Float64Array',
    'BigInt64Array',
    'BigUint64Array',
]);
/**
 * Checks if the provided node is a JS typed array like "BigInt64Array". See TYPED_ARRAY_TYPES
 *
 * @param node
 * @param services
 * @returns
 */
function isTypedArray(node, services) {
    const type = getTypeFromTreeNode(node, services);
    return TYPED_ARRAY_TYPES.has(type.symbol?.name);
}
function isString(node, services) {
    const checker = services.program.getTypeChecker();
    const typ = checker.getTypeAtLocation(services.esTreeNodeToTSNodeMap.get(node));
    return (typ.getFlags() & typescript_1.default.TypeFlags.StringLike) !== 0;
}
function isNumber(node, services) {
    const checker = services.program.getTypeChecker();
    const typ = checker.getTypeAtLocation(services.esTreeNodeToTSNodeMap.get(node));
    return (typ.getFlags() & typescript_1.default.TypeFlags.NumberLike) !== 0;
}
function isBigIntType(type) {
    return (type.getFlags() & typescript_1.default.TypeFlags.BigIntLike) !== 0;
}
function isNumberType(type) {
    return (type.getFlags() & typescript_1.default.TypeFlags.NumberLike) !== 0;
}
function isStringType(type) {
    return (type.flags & typescript_1.default.TypeFlags.StringLike) > 0 || type.symbol?.name === 'String';
}
function isFunction(node, services) {
    const checker = services.program.getTypeChecker();
    const type = checker.getTypeAtLocation(services.esTreeNodeToTSNodeMap.get(node));
    return type.symbol && (type.symbol.flags & typescript_1.default.SymbolFlags.Function) !== 0;
}
function isUnion(node, services) {
    const checker = services.program.getTypeChecker();
    const type = checker.getTypeAtLocation(services.esTreeNodeToTSNodeMap.get(node));
    return type.isUnion();
}
/**
 * Returns an array of the union types if the provided type is a union.
 * Otherwise, returns an array containing the provided type as its unique element.
 * @param type A TypeScript type.
 * @return An array of types. It's never empty.
 */
function getUnionTypes(type) {
    return type.isUnion() ? type.types : [type];
}
function isUndefinedOrNull(node, services) {
    const checker = services.program.getTypeChecker();
    const typ = checker.getTypeAtLocation(services.esTreeNodeToTSNodeMap.get(node));
    return ((typ.getFlags() & typescript_1.default.TypeFlags.Undefined) !== 0 || (typ.getFlags() & typescript_1.default.TypeFlags.Null) !== 0);
}
function isThenable(node, services) {
    const mapped = services.esTreeNodeToTSNodeMap.get(node);
    const checker = services.program.getTypeChecker();
    return hasThenMethod(checker.getTypeAtLocation(mapped), checker);
}
/**
 * Checks if a node's type is either:
 * - Thenable (Promise-like), OR
 * - A union where ALL members are either thenable or "nothing" types (void, undefined, null)
 *
 * This is useful for rules like S3735 that allow voiding Promise operations,
 * including cases like optional chaining (Promise<T> | undefined) or
 * optional async callbacks (() => void | Promise<void>).
 */
function isThenableOrVoidUnion(node, services) {
    const checker = services.program.getTypeChecker();
    const type = getTypeFromTreeNode(node, services);
    const unionTypes = type.isUnion() ? type.types : [type];
    let hasThenable = false;
    let allThenableOrVoid = true;
    for (const unionType of unionTypes) {
        const isThenable = hasThenMethod(unionType, checker);
        const isNothingType = (unionType.flags & (typescript_1.default.TypeFlags.Void | typescript_1.default.TypeFlags.Undefined | typescript_1.default.TypeFlags.Null)) !== 0;
        hasThenable ||= isThenable;
        allThenableOrVoid &&= isThenable || isNothingType;
    }
    return hasThenable && allThenableOrVoid;
}
function hasThenMethod(type, checker) {
    const thenProperty = type.getProperty('then');
    if (!thenProperty) {
        return false;
    }
    const thenType = checker.getTypeOfSymbol(thenProperty);
    return thenType.getCallSignatures().length > 0;
}
function isAny(type) {
    return type.flags === typescript_1.default.TypeFlags.Any;
}
/**
 * Checks if a node has a generic type like:
 *
 * function foo<T> (bar: T) {
 *    bar // is generic
 * }
 *
 * @param node TSESTree.Node
 * @param services RuleContext.parserServices
 * @returns
 */
function isGenericType(node, services) {
    const type = getTypeFromTreeNode(node, services);
    return type.isTypeParameter();
}
function getTypeFromTreeNode(node, services) {
    const checker = services.program.getTypeChecker();
    return checker.getTypeAtLocation(services.esTreeNodeToTSNodeMap.get(node));
}
function getTypeAsString(node, services) {
    const { typeToString, getBaseTypeOfLiteralType } = services.program.getTypeChecker();
    return typeToString(getBaseTypeOfLiteralType(getTypeFromTreeNode(node, services)));
}
function getSymbolAtLocation(node, services) {
    const checker = services.program.getTypeChecker();
    return checker.getSymbolAtLocation(services.esTreeNodeToTSNodeMap.get(node));
}
function getSignatureFromCallee(node, services) {
    const checker = services.program.getTypeChecker();
    return checker.getResolvedSignature(services.esTreeNodeToTSNodeMap.get(node));
}
/**
 * This function checks if a type may correspond to an array type. Beyond simple array types, it will also
 * consider the union of array types and generic types extending an array type.
 * @param type A type to check
 * @param services The services used to get access to the TypeScript type checker
 */
function isArrayLikeType(type, services) {
    const checker = services.program.getTypeChecker();
    const constrained = checker.getBaseConstraintOfType(type);
    return isArrayOrUnionOfArrayType(constrained ?? type, services);
}
function isArrayOrUnionOfArrayType(type, services) {
    for (const part of getUnionTypes(type)) {
        if (!isArrayType(part, services)) {
            return false;
        }
    }
    return true;
}
/**
 * Test if the provided type is an array of strings.
 * @param type A TypeScript type.
 * @param services The services used to get access to the TypeScript type checker
 */
function isStringArray(type, services) {
    return isArrayElementTypeMatching(type, services, isStringType);
}
/**
 * Test if the provided type is an array of numbers.
 * @param type A TypeScript type.
 * @param services The services used to get access to the TypeScript type checker
 */
function isNumberArray(type, services) {
    return isArrayElementTypeMatching(type, services, isNumberType);
}
/**
 * Test if the provided type is an array of big integers.
 * @param type A TypeScript type.
 * @param services The services used to get access to the TypeScript type checker
 */
function isBigIntArray(type, services) {
    return isArrayElementTypeMatching(type, services, isBigIntType);
}
function isArrayElementTypeMatching(type, services, predicate) {
    const checker = services.program.getTypeChecker();
    if (!isArrayType(type, services)) {
        return false;
    }
    const [elementType] = checker.getTypeArguments(type);
    return elementType && predicate(elementType);
}
// Internal TS API
function isArrayType(type, services) {
    const checker = services.program.getTypeChecker();
    return ('isArrayType' in checker &&
        typeof checker.isArrayType === 'function' &&
        checker.isArrayType(type));
}
/**
 * Checks whether a TypeScript type node denotes a type alias.
 * @param node a type node to check
 * @param context the rule context
 */
function isTypeAlias(node, context) {
    if (node.type !== 'TSTypeReference' ||
        node.typeName.type !== 'Identifier' ||
        node.typeArguments) {
        return false;
    }
    const scope = context.sourceCode.getScope(node);
    const variable = (0, ast_js_1.getVariableFromScope)(scope, node.typeName.name);
    return variable?.defs.some(def => def.node.type === 'TSTypeAliasDeclaration');
}
function isBooleanLiteralType(type) {
    return type.flags === typescript_1.default.TypeFlags.BooleanLiteral;
}
function isBooleanTrueType(type) {
    return isBooleanLiteralType(type) && type.intrinsicName === 'true';
}
function isBooleanType({ flags }) {
    return flags & typescript_1.default.TypeFlags.BooleanLike;
}
function isNullOrUndefinedType({ flags }) {
    return flags & typescript_1.default.TypeFlags.Null || flags & typescript_1.default.TypeFlags.Undefined;
}
function isObjectType({ flags }) {
    return flags & typescript_1.default.TypeFlags.Object;
}
function typeHasMethod(node, methodName, services) {
    const type = getTypeFromTreeNode(node, services);
    const property = type.getProperty(methodName);
    if (!property) {
        return false;
    }
    // Check if it's a method by examining the symbol flags
    if (property.flags & typescript_1.default.SymbolFlags.Method) {
        return true;
    }
    // Also check if it's a property that contains a function
    if (property.flags & typescript_1.default.SymbolFlags.Property) {
        const typeChecker = services.program.getTypeChecker();
        const propertyType = property.valueDeclaration
            ? typeChecker.getTypeOfSymbolAtLocation(property, property.valueDeclaration)
            : typeChecker.getTypeOfSymbol(property);
        // Check if the property type is callable (has call signatures)
        return propertyType.getCallSignatures().length > 0;
    }
    return false;
}
/**
 * Checks if a type is iterable (can be used in for-of loops).
 * @param node The node to check
 * @param services The parser services
 * @returns true if the type is iterable, false otherwise
 */
function isIterable(node, services) {
    const type = getTypeFromTreeNode(node, services);
    const properties = type.getProperties();
    return properties.some(prop => prop.name.startsWith('__@iterator@'));
}
/**
 * Gets the number of parameters for a function-typed node using TypeScript type information.
 * Returns null if the parameter count cannot be determined.
 *
 * For functions with multiple call signatures (overloads), returns the maximum
 * parameter count across all signatures.
 *
 * @param node The node to get parameter count for
 * @param services TypeScript parser services
 * @returns The parameter count, or null if it cannot be determined
 */
function getFunctionParameterCount(node, services) {
    try {
        const type = getTypeFromTreeNode(node, services);
        const signatures = type.getCallSignatures();
        if (signatures.length === 0) {
            return null;
        }
        // Return the maximum parameter count across all signatures
        // (handles function overloads)
        return Math.max(...signatures.map(sig => sig.parameters.length));
    }
    catch {
        return null;
    }
}
