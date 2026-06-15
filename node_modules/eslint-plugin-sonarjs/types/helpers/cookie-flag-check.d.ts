import type { Rule } from 'eslint';
import type estree from 'estree';
export declare class CookieFlagCheck {
    readonly context: Rule.RuleContext;
    readonly flag: 'httpOnly' | 'secure';
    issueMessage: string;
    constructor(context: Rule.RuleContext, flag: 'httpOnly' | 'secure');
    private checkCookieSession;
    private checkCookiesMethodCall;
    private checkCsurf;
    private checkExpressSession;
    private checkSensitiveCookieArgument;
    private checkSensitiveObjectArgument;
    private checkFlagOnCookieExpression;
    checkCookiesFromCallExpression(node: estree.Node): void;
}
