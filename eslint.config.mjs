import { defineConfig } from "eslint/config";
import safeword from "safeword/eslint";

// Prettier config is bundled with safeword
const eslintConfigPrettier = safeword.prettierConfig;

const { detect, configs } = safeword;
const __dirname = import.meta.dirname;
const deps = detect.collectAllDeps(__dirname);
const framework = detect.detectFramework(deps);

// Monorepo support: detect Next.js apps to scope Next.js-only rules
// - Returns undefined for single-app Next.js projects (use full Next config)
// - Returns string[] of glob patterns for monorepos (scope Next.js rules)
const nextPaths = detect.findNextConfigPaths(__dirname);

// Map framework to base config
// Note: Astro config only lints .astro files, so we combine it with TypeScript config
// to also lint .ts files in Astro projects
// Note: In monorepos, Next.js uses React config + scoped Next.js rules
const baseConfigs = {
  next: nextPaths ? configs.recommendedTypeScriptReact : configs.recommendedTypeScriptNext,
  react: configs.recommendedTypeScriptReact,
  astro: [...configs.recommendedTypeScript, ...configs.astro],
  typescript: configs.recommendedTypeScript,
  javascript: configs.recommended,
};

// Build scoped Next.js rules for monorepos
// Each Next.js app gets its own scoped config with files: pattern
const scopedNextConfigs = nextPaths?.flatMap((filePath) =>
  configs.nextOnlyRules.map((config) => ({ ...config, files: [filePath] }))
) ?? [];

export default defineConfig([
  { ignores: detect.getIgnores() },
  ...baseConfigs[framework],
  ...scopedNextConfigs,
  // Testing configs - only if detected (plugins have framework peer deps)
  ...(detect.hasVitest(deps) ? configs.vitest : []),
  ...(detect.hasPlaywright(deps) ? configs.playwright : []),
  // Storybook - only if detected (v10+ requires storybook peer dep)
  ...(detect.hasStorybook(deps) ? configs.storybook : []),
  // TanStack Query - only if detected (has typescript peer dep)
  ...(detect.hasTanstackQuery(deps) ? configs.tanstackQuery : []),
  // Tailwind - only if detected (plugin needs tailwind config to validate classes)
  ...(detect.hasTailwind(deps) ? configs.tailwind : []),
  // Turborepo - only if detected (validates env vars are declared in turbo.json)
  ...(detect.hasTurbo(deps) ? configs.turbo : []),
  eslintConfigPrettier,
]);
