# is-document.all <sup>[![Version Badge][2]][1]</sup>

[![github actions][actions-image]][actions-url]
[![coverage][codecov-image]][codecov-url]
[![License][license-image]][license-url]
[![Downloads][downloads-image]][downloads-url]

[![npm badge][11]][1]

Is this value `document.all`, i.e. an object with the [[IsHTMLDDA]] internal slot?

## Example

```js
var isDocumentAll = require('is-document.all');
var assert = require('assert');

assert(!isDocumentAll(undefined));
assert(!isDocumentAll(null));
assert(!isDocumentAll({}));
assert(!isDocumentAll(function () {}));

// in a browser:
assert(isDocumentAll(document.all));
```

## Tests
Simply clone the repo, `npm install`, and run `npm test`

[1]: https://npmjs.org/package/is-document.all
[2]: https://versionbadg.es/inspect-js/is-document.all.svg
[11]: https://nodei.co/npm/is-document.all.png?downloads=true&stars=true
[license-image]: https://img.shields.io/npm/l/is-document.all.svg
[license-url]: LICENSE
[downloads-image]: https://img.shields.io/npm/dm/is-document.all.svg
[downloads-url]: https://npm-stat.com/charts.html?package=is-document.all
[codecov-image]: https://codecov.io/gh/inspect-js/is-document.all/branch/main/graphs/badge.svg
[codecov-url]: https://app.codecov.io/gh/inspect-js/is-document.all/
[actions-image]: https://img.shields.io/github/check-runs/inspect-js/is-document.all/main
[actions-url]: https://github.com/inspect-js/is-document.all/actions
