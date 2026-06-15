"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.generateMeta = generateMeta;
const lodash_merge_1 = __importDefault(require("lodash.merge"));
function generateMeta(sonarMeta, ruleMeta) {
    if (!!sonarMeta.meta.fixable !== !!(ruleMeta?.fixable || ruleMeta?.hasSuggestions)) {
        throw new Error(`Mismatch between RSPEC metadata and implementation for fixable attribute in rule ${sonarMeta.meta.docs.url}`);
    }
    if (ruleMeta?.fixable && !sonarMeta.quickFixMessage) {
        throw new Error(`Rule ${sonarMeta.sonarKey} is marked as fixable but no quick fix message is provided.`);
    }
    // sonarMeta should overwrite eslint metadata for decorated rules, our titles and docs should be shown instead
    const metadata = {
        ...ruleMeta,
        ...sonarMeta.meta,
        schema: sonarMeta.schema ?? ruleMeta?.schema,
    };
    // If rules contains default options, we will augment them with our defaults.
    if (ruleMeta?.defaultOptions) {
        metadata.defaultOptions = (0, lodash_merge_1.default)(ruleMeta.defaultOptions, sonarMeta.meta.defaultOptions);
    }
    // RSPEC metadata can include fixable also for rules with suggestions, because RSPEC doesn't differentiate between fix
    // and suggestion like ESLint does. That's why we set fixable using ruleMeta
    metadata.fixable = ruleMeta?.fixable;
    metadata.messages ??= {};
    if (sonarMeta.hasSecondaries) {
        metadata.messages.sonarRuntime = '{{sonarRuntimeData}}';
    }
    return metadata;
}
