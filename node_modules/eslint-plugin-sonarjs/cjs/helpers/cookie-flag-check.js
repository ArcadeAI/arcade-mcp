"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.CookieFlagCheck = void 0;
const location_js_1 = require("./location.js");
const ast_js_1 = require("./ast.js");
const module_js_1 = require("./module.js");
class CookieFlagCheck {
    constructor(context, flag) {
        this.context = context;
        this.flag = flag;
        this.issueMessage = `Make sure creating this cookie without the "${flag}" flag is safe.`;
    }
    checkCookieSession(callExpression) {
        // Sensitive argument for cookie session is first one
        this.checkSensitiveCookieArgument(callExpression, 0);
    }
    checkCookiesMethodCall(callExpression) {
        if (!(0, ast_js_1.isIdentifier)(callExpression.callee.property, 'set')) {
            return;
        }
        // Sensitive argument is third argument for "cookies.set" calls
        this.checkSensitiveCookieArgument(callExpression, 2);
    }
    checkCsurf(callExpression) {
        // Sensitive argument is first for csurf
        const cookieProperty = this.checkSensitiveObjectArgument(callExpression, 0);
        if (cookieProperty) {
            // csurf cookie property can be passed as a boolean literal,
            // in which case neither "secure" nor "httponly" are enabled by default
            const cookiePropertyLiteral = (0, ast_js_1.getValueOfExpression)(this.context, cookieProperty.value, 'Literal');
            if (cookiePropertyLiteral?.value === true) {
                (0, location_js_1.report)(this.context, {
                    node: callExpression.callee,
                    message: this.issueMessage,
                }, [(0, location_js_1.toSecondaryLocation)(cookiePropertyLiteral)]);
            }
        }
    }
    checkExpressSession(callExpression) {
        // Sensitive argument is first for express-session
        this.checkSensitiveObjectArgument(callExpression, 0);
    }
    checkSensitiveCookieArgument(callExpression, sensitiveArgumentIndex) {
        if (callExpression.arguments.length < sensitiveArgumentIndex + 1) {
            return;
        }
        const sensitiveArgument = callExpression.arguments[sensitiveArgumentIndex];
        const cookieObjectExpression = (0, ast_js_1.getValueOfExpression)(this.context, sensitiveArgument, 'ObjectExpression');
        if (!cookieObjectExpression) {
            return;
        }
        this.checkFlagOnCookieExpression(cookieObjectExpression, sensitiveArgument, cookieObjectExpression, callExpression);
    }
    checkSensitiveObjectArgument(callExpression, argumentIndex) {
        if (callExpression.arguments.length < argumentIndex + 1) {
            return;
        }
        const firstArgument = callExpression.arguments[argumentIndex];
        const objectExpression = (0, ast_js_1.getValueOfExpression)(this.context, firstArgument, 'ObjectExpression');
        if (!objectExpression) {
            return;
        }
        const cookieProperty = (0, ast_js_1.getProperty)(objectExpression, 'cookie', this.context);
        if (!cookieProperty) {
            return;
        }
        const cookiePropertyValue = (0, ast_js_1.getValueOfExpression)(this.context, cookieProperty.value, 'ObjectExpression');
        if (cookiePropertyValue) {
            this.checkFlagOnCookieExpression(cookiePropertyValue, firstArgument, objectExpression, callExpression);
            return;
        }
        return cookieProperty;
    }
    checkFlagOnCookieExpression(cookiePropertyValue, firstArgument, objectExpression, callExpression) {
        const flagProperty = (0, ast_js_1.getProperty)(cookiePropertyValue, this.flag, this.context);
        if (flagProperty) {
            const flagPropertyValue = (0, ast_js_1.getValueOfExpression)(this.context, flagProperty.value, 'Literal');
            if (flagPropertyValue?.value === false) {
                const secondaryLocations = [(0, location_js_1.toSecondaryLocation)(flagPropertyValue)];
                if (firstArgument !== objectExpression) {
                    secondaryLocations.push((0, location_js_1.toSecondaryLocation)(objectExpression));
                }
                (0, location_js_1.report)(this.context, {
                    node: callExpression.callee,
                    message: this.issueMessage,
                }, secondaryLocations);
            }
        }
    }
    checkCookiesFromCallExpression(node) {
        const callExpression = node;
        const { callee } = callExpression;
        const fqn = (0, module_js_1.getFullyQualifiedName)(this.context, callee);
        if (fqn === 'cookie-session') {
            this.checkCookieSession(callExpression);
            return;
        }
        if (fqn === 'csurf') {
            this.checkCsurf(callExpression);
            return;
        }
        if (fqn === 'express-session') {
            this.checkExpressSession(callExpression);
            return;
        }
        if (callee.type === 'MemberExpression') {
            const objectValue = (0, ast_js_1.getValueOfExpression)(this.context, callee.object, 'NewExpression');
            if (objectValue && (0, module_js_1.getFullyQualifiedName)(this.context, objectValue.callee) === 'cookies') {
                this.checkCookiesMethodCall(callExpression);
            }
        }
    }
}
exports.CookieFlagCheck = CookieFlagCheck;
