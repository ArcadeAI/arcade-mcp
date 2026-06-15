/**
 * Dependency Cruiser Configuration
 *
 * Imports auto-generated rules from .safeword/depcruise-config.cjs
 * ADD YOUR CUSTOM RULES BELOW the spread operator.
 */

const generated = require('./.safeword/depcruise-config.cjs');

module.exports = {
  forbidden: [
    ...generated.forbidden,
    // ADD YOUR CUSTOM RULES BELOW:
    // { name: 'no-legacy', from: { path: 'legacy/' }, to: { path: 'new/' } },
  ],
  options: {
    ...generated.options,
    // Your overrides here
  },
};
