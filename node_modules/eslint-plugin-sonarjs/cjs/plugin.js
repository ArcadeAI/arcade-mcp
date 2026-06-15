"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.rules = exports.meta = exports.configs = void 0;
const plugin_rules_js_1 = require("./plugin-rules.js");
const recommendedLegacyConfig = { plugins: ['sonarjs'], rules: {} };
const recommendedConfig = {
    name: 'sonarjs/recommended',
    plugins: {
        sonarjs: {
            rules: plugin_rules_js_1.rules,
        },
    },
    rules: {},
    settings: {
        react: {
            version: '999.999.999',
        },
    },
};
for (const [key, rule] of Object.entries(plugin_rules_js_1.rules)) {
    const recommended = rule.meta?.docs?.recommended || false;
    recommendedConfig.rules[`sonarjs/${key}`] = recommended ? 'error' : 'off';
}
recommendedLegacyConfig.rules = recommendedConfig.rules;
recommendedLegacyConfig.settings = recommendedConfig.settings;
exports.configs = {
    recommended: recommendedConfig,
    'recommended-legacy': recommendedLegacyConfig,
};
/**
 * I kept the meta export for compatibility, but we need to find a way to populate it without relying on the package manifest
 */
exports.meta = {
    name: 'eslint-plugin-sonarjs',
    version: '0.0.0-SNAPSHOT',
};
const plugin = { rules: plugin_rules_js_1.rules, configs: exports.configs, meta: exports.meta };
exports.default = plugin;
var plugin_rules_js_2 = require("./plugin-rules.js");
Object.defineProperty(exports, "rules", { enumerable: true, get: function () { return plugin_rules_js_2.rules; } });
