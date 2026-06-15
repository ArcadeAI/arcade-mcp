// cucumber-js config — safeword's BDD acceptance lane, separate from your unit
// tests. `tsx/esm` transpiles the TypeScript step definitions on the fly;
// `paths` are the Gherkin `.feature` files. Run via `npm run test:bdd` (or
// `bun run test:bdd`). Safeword owns this file; step definitions and features
// are yours.
const workspaceFeaturePaths = [
  'features/**/*.feature',
  'packages/*/features/**/*.feature',
  'apps/*/features/**/*.feature',
  'libs/*/features/**/*.feature',
  'modules/*/features/**/*.feature',
];

const workspaceStepImports = [
  'tsx/esm',
  'steps/**/*.ts',
  'packages/*/features/steps/**/*.ts',
  'apps/*/features/steps/**/*.ts',
  'libs/*/features/steps/**/*.ts',
  'modules/*/features/steps/**/*.ts',
];

export default {
  import: workspaceStepImports,
  paths: workspaceFeaturePaths,
  tags: 'not @manual and not @live',
};
