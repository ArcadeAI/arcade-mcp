# es-iterator-helpers <sup>[![Version Badge][npm-version-svg]][package-url]</sup>

[![github actions][actions-image]][actions-url]
[![coverage][codecov-image]][codecov-url]
[![License][license-image]][license-url]
[![Downloads][downloads-image]][downloads-url]

[![npm badge][npm-badge-png]][package-url]

An ESnext spec-compliant sync iterator helpers shim/polyfill/replacement that works as far down as ES3.

This package implements the [es-shim API](https://github.com/es-shims/api) “multi” interface. It works in an ES3-supported environment and complies with the [iterator helpers spec](https://tc39.es/proposal-iterator-helpers/) and the [iterator sequencing spec](https://tc39.es/proposal-iterator-sequencing/).

Because the `Iterator.prototype` methods depend on a receiver (the `this` value), the main export in each subdirectory takes the iterator to operate on as the first argument.

The main export of the package itself is simply an array of the available directory names. It’s sole intended use is for build tooling and testing.

## Supported things

 - [`Iterator` constructor](https://tc39.es/proposal-iterator-helpers/#sec-iterator-constructor)
 - [`Iterator.prototype`](https://tc39.es/proposal-iterator-helpers/#sec-iterator.prototype)
 - [`Iterator.concat`](https://tc39.es/proposal-iterator-sequencing/)
 - [`Iterator.from`](https://tc39.es/proposal-iterator-helpers/#sec-iterator.from)
 - [`Iterator.zip`](https://tc39.es/proposal-joint-iteration/#sec-iterator.zip)
 - [`Iterator.zipKeyed`](https://tc39.es/proposal-joint-iteration/#sec-iterator.zipkeyed)
 - [`Iterator.prototype.constructor`](https://tc39.es/proposal-iterator-helpers/#sec-iteratorprototype.constructor)
 - [`Iterator.prototype.drop`](https://tc39.es/proposal-iterator-helpers/#sec-iteratorprototype.drop)
 - [`Iterator.prototype.every`](https://tc39.es/proposal-iterator-helpers/#sec-iteratorprototype.every)
 - [`Iterator.prototype.filter`](https://tc39.es/proposal-iterator-helpers/#sec-iteratorprototype.filter)
 - [`Iterator.prototype.find`](https://tc39.es/proposal-iterator-helpers/#sec-iteratorprototype.find)
 - [`Iterator.prototype.flatMap`](https://tc39.es/proposal-iterator-helpers/#sec-iteratorprototype.flatmap)
 - [`Iterator.prototype.forEach`](https://tc39.es/proposal-iterator-helpers/#sec-iteratorprototype.foreach)
 - [`Iterator.prototype.includes`](https://tc39.es/proposal-iterator-includes/)
 - [`Iterator.prototype.map`](https://tc39.es/proposal-iterator-helpers/#sec-iteratorprototype.map)
 - [`Iterator.prototype.reduce`](https://tc39.es/proposal-iterator-helpers/#sec-iteratorprototype.reduce)
 - [`Iterator.prototype.some`](https://tc39.es/proposal-iterator-helpers/#sec-iteratorprototype.some)
 - [`Iterator.prototype.take`](https://tc39.es/proposal-iterator-helpers/#sec-iteratorprototype.take)
 - [`Iterator.prototype.toArray`](https://tc39.es/proposal-iterator-helpers/#sec-iteratorprototype.toarray)

## Environments where this is needed

 - node < v22, Chrome < v122, Safari <= v17.1, Firefox <= v125: not implemented
 - node v22, Chrome v122 - v130: has a [bug](https://issues.chromium.org/issues/336839115) where `{ next: null }` is not properly rejected
 - node v22 - v24, Chrome v122 - v134: missing early-error `IteratorClose` when argument validation fails (e.g., non-callable mapper does not call the iterator's `return` method)
 - all environments lack Iterator.concat, Iterator.zip, Iterator.zipKeyed, Iterator.prototype.includes

## Getting started

```sh
npm install --save es-iterator-helpers
```

## Usage/Examples

Using explicit imports:

```js
const map = require('es-iterator-helpers/Iterator.prototype.map');
const toArray = require('es-iterator-helpers/Iterator.prototype.toArray');
const assert = require('assert');

const iterator = [1, 2, 3].values();

const mapped = map(iterator, (x) => x + 10);
assert.deepEqual(
	mapped.next(),
    {
        done: false,
        value: 11,
    }
);
assert.deepEqual(
    toArray(mapped),
    [12, 13]
);
```

Shim using `require`:

```js
require('es-iterator-helpers/auto'); // shim all of the methods

require('es-iterator-helpers/Iterator.prototype.map/auto'); // shim the “map” method
```

Shim using `import` syntax:

[](#preventEval)
```js
import 'es-iterator-helpers/auto'; // shim all of the methods

import 'es-iterator-helpers/Iterator.prototype.map/auto'; // shim the “map” method
```

## Tests
Simply clone the repo, `npm install`, and run `npm test`

Additionally, the official [test262](https://github.com/tc39/test262) Iterator suite is included as a git submodule and can be run against the shim with `npm run test262`
(in CI this runs across a range of Node versions, from one with no native iterator helpers up to the current LTS).
Initialize the submodule first with `git submodule update --init --depth 1` (or clone with `--recurse-submodules`).

[package-url]: https://npmjs.org/package/es-iterator-helpers
[npm-version-svg]: https://versionbadg.es/es-shims/iterator-helpers.svg
[deps-svg]: https://david-dm.org/es-shims/iterator-helpers.svg
[deps-url]: https://david-dm.org/es-shims/iterator-helpers
[dev-deps-svg]: https://david-dm.org/es-shims/iterator-helpers/dev-status.svg
[dev-deps-url]: https://david-dm.org/es-shims/iterator-helpers#info=devDependencies
[npm-badge-png]: https://nodei.co/npm/es-iterator-helpers.png?downloads=true&stars=true
[license-image]: https://img.shields.io/npm/l/es-iterator-helpers.svg
[license-url]: LICENSE
[downloads-image]: https://img.shields.io/npm/dm/es-iterator-helpers.svg
[downloads-url]: https://npm-stat.com/charts.html?package=es-iterator-helpers
[codecov-image]: https://codecov.io/gh/es-shims/iterator-helpers/branch/main/graphs/badge.svg
[codecov-url]: https://app.codecov.io/gh/es-shims/iterator-helpers/
[actions-image]: https://img.shields.io/github/check-runs/es-shims/iterator-helpers/main
[actions-url]: https://github.com/es-shims/iterator-helpers/actions
