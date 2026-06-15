# node-exports-info <sup>[![Version Badge][npm-version-svg]][package-url]</sup>

[![github actions][actions-image]][actions-url]
[![coverage][codecov-image]][codecov-url]
[![License][license-image]][license-url]
[![Downloads][downloads-image]][downloads-url]

[![npm badge][npm-badge-png]][package-url]

Info about node `exports` field support: version ranges, categories, etc.

## Categories
 - `pre-exports`: versions before node supported `exports` in any way (`< 12.17`)
 - `broken`: versions that have a broken `exports` implementation. These only support the string form, and array fallbacks. (`13.0 - 13.2`)
 - `experimental`: versions where `exports` support was experimental. These only support the “default” condition in the object form. (`13.3 - 13.6`)
 - `conditions`: the first versions where `exports` support was unflagged. (`13.7 - 13.12`)
 - `broken-dir-slash-conditions`: `conditions`, but directory exports (ending in `./`) are broken in these versions (`12.17 - 12.19 || ^13.13 || 14.0 - 14.12`)
 - `patterns`: support for “patterns” was added in these versions, and directory exports (ending in `./`) are broken (`^12.20 || 14.13 - 14.18 || 15.x || 16.0 - 16.8`)
 - `pattern-trailers`: support for “pattern trailers” was added in these versions (`^14.19 || 16.9 - 16.13`)
 - `pattern-trailers+json-imports`: `pattern-trailers`, and JSON can be `import`ed (`^16.14`)
 - `pattern-trailers-no-dir-slash`: support for directory exports (ending in `./`) was removed for these versions (`17.0`)
 - `pattern-trailers-no-dir-slash+json-imports`: `pattern-trailers-no-dir-slash`, and JSON can be `import`ed (`17.1 - 19 || 20 - 20.18 || ^21 || 22 - 22.11`)
 - `require-esm`: ESM files can be `require`d (`23 - 23.5 || 22.12 - 22.17 || ^20.19`)
 - `strips-types`: these versions also automatically strip types from typescript files, for both `require` and `import` (`23.6 - 25.3 || ^22.18`)
 - `subpath-imports-slash`: these versions support `#/` subpath imports patterns in the `imports` field, e.g. `"#/*": "./src/*.js"` (`>= 25.4`)

## Entry points
 - `node-exports-info/getCategoriesForRange`: takes a node semver version range; returns an array of categories that overlap it
 - `node-exports-info/getCategory`: takes an optional node semver version (defaults to the current node version); returns the latest category that matches it
 - `node-exports-info/getCategoryFlags`: takes a category; returns an object with boolean flags `{ patterns, patternTrailers, dirSlash }` indicating which `exports` features are supported
 - `node-exports-info/getCategoryInfo`: takes a category and an optional `moduleSystem` (`'require'` or `'import'`); returns an object with `conditions` (array or null) and `flags` (from `getCategoryFlags`)
 - `node-exports-info/getConditionsForCategory`: takes a category and an optional `moduleSystem` (`'require'` or `'import'`); returns an array of `exports` "conditions" that is supported, or `null` if `exports` itself is not supported
 - `node-exports-info/getRange`: takes a category; returns the node semver version range that matches it
 - `node-exports-info/getRangePairs`: returns an array of entries - each a tuple of “semver range” and “category”
 - `node-exports-info/isCategory`: takes a category; returns true if it’s a known category

## Related packages
 - [`has-package-exports`](https://www.npmjs.com/package/has-package-exports): feature-detect your node version’s `exports` support

## Tests
Simply clone the repo, `npm install`, and run `npm test`

[package-url]: https://npmjs.org/package/node-exports-info
[npm-version-svg]: https://versionbadg.es/inspect-js/node-exports-info.svg
[deps-svg]: https://david-dm.org/inspect-js/node-exports-info.svg
[deps-url]: https://david-dm.org/inspect-js/node-exports-info
[dev-deps-svg]: https://david-dm.org/inspect-js/node-exports-info/dev-status.svg
[dev-deps-url]: https://david-dm.org/inspect-js/node-exports-info#info=devDependencies
[npm-badge-png]: https://nodei.co/npm/node-exports-info.png?downloads=true&stars=true
[license-image]: https://img.shields.io/npm/l/node-exports-info.svg
[license-url]: LICENSE
[downloads-image]: https://img.shields.io/npm/dm/node-exports-info.svg
[downloads-url]: https://npm-stat.com/charts.html?package=node-exports-info
[codecov-image]: https://codecov.io/gh/inspect-js/node-exports-info/branch/main/graphs/badge.svg
[codecov-url]: https://app.codecov.io/gh/inspect-js/node-exports-info/
[actions-image]: https://img.shields.io/github/check-runs/inspect-js/node-exports-info/main
[actions-url]: https://github.com/inspect-js/node-exports-info/actions
