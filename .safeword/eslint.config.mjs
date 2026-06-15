// Safeword ESLint config - extends project config with stricter rules
// Used by hooks for LLM enforcement. Human pre-commits use project config.
// Re-run `safeword upgrade` to regenerate after project config changes.
import { existsSync } from "node:fs";
import safeword from "safeword/eslint";
const eslintConfigPrettier = safeword.prettierConfig;

// Ticket 139: existsSync gate + no try/catch.
// - File present, import fails → real error (syntax, missing plugin, etc.) → throw,
//   so the hook fails loud instead of silently dropping customer overrides.
// - File absent → projectConfig stays [] → hook runs with safeword defaults only.
//   In practice, safeword's managedFiles generates the project eslint.config.mjs
//   in the same setup run, so this fallback only fires in degenerate cases.
let projectConfig = [];
const projectConfigPath = new URL("../eslint.config.mjs", import.meta.url);
if (existsSync(projectConfigPath)) {
  projectConfig = (await import("../eslint.config.mjs")).default;
  if (!Array.isArray(projectConfig)) {
    projectConfig = [projectConfig];
  }
}

// Safeword strict rules - applied after project rules (win on conflict)
const safewordStrictRules = {
  rules: {
    // Prevent common LLM mistakes
    "no-unused-vars": ["error", { argsIgnorePattern: "^_", varsIgnorePattern: "^_" }],
    "no-undef": "error",
    "no-unreachable": "error",
    "no-constant-condition": "error",
    "no-empty": "error",
    "no-extra-semi": "error",
    "no-func-assign": "error",
    "no-import-assign": "error",
    "no-invalid-regexp": "error",
    "no-irregular-whitespace": "error",
    "no-loss-of-precision": "error",
    "no-misleading-character-class": "error",
    "no-prototype-builtins": "error",
    "no-unexpected-multiline": "error",
    "no-unsafe-finally": "error",
    "no-unsafe-negation": "error",
    "use-isnan": "error",
    "valid-typeof": "error",
    // Strict code quality
    "eqeqeq": ["error", "always", { null: "ignore" }],
    "no-var": "error",
    "prefer-const": "error",
  },
};

// Composition order (ticket 138): safeword rules FIRST, customer config LAST.
// Flat config is "later wins" — this makes the customer's project config
// authoritative for the LLM hook. Customer overrides (e.g. 'no-unused-vars': 'off')
// take effect here instead of being silently overridden by safeword's strict layer.
export default [
  safewordStrictRules,
  ...projectConfig,
  eslintConfigPrettier,
];
