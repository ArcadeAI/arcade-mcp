# @teppeis/multimaps

Multi-Map classes for TypeScript and JavaScript

[![npm version][npm-image]][npm-url]
![Node.js Version Support][node-version]
![TypeScript Version Support][ts-version]
[![build status][ci-image]][ci-url]
![dependency status][deps-count-image]
![monthly downloads][npm-downloads-image]
![License][license]

## Install

```console
$ npm i @teppeis/multimaps
```

## Usage

### `ArrayMultimap`

```js
import {ArrayMultimap} from '@teppeis/multimaps';

const map = new ArrayMultimap<string, string>();
map.put('foo', 'a');
map.get('foo'); // ['a']
map.put('foo', 'b');
map.get('foo'); // ['a', 'b']
map.put('foo', 'a');
map.get('foo'); // ['a', 'b', 'a']
```

### `SetMultimap`

```js
import {SetMultimap} from '@teppeis/multimaps';

const map = new SetMultimap<string, string>();
map.put('foo', 'a');
map.get('foo'); // a `Set` of ['a']
map.put('foo', 'b');
map.get('foo'); // a `Set` of ['a', 'b']
map.put('foo', 'a');
map.get('foo'); // a `Set` of ['a', 'b']
```

## License

MIT License: Teppei Sato &lt;teppeis@gmail.com&gt;

[npm-image]: https://badgen.net/npm/v/@teppeis/multimaps?icon=npm&label=
[npm-url]: https://npmjs.org/package/@teppeis/multimaps
[npm-downloads-image]: https://badgen.net/npm/dm/@teppeis/multimaps
[deps-image]: https://badgen.net/david/dep/teppeis/multimaps.svg
[deps-url]: https://david-dm.org/teppeis/multimaps
[deps-count-image]: https://badgen.net/bundlephobia/dependency-count/@teppeis/multimaps
[node-version]: https://badgen.net/npm/node/@teppeis/multimaps
[ts-version]: https://badgen.net/badge/typescript/%3E=4.0?icon=typescript
[license]: https://img.shields.io/npm/l/@teppeis/multimaps.svg
[ci-image]: https://github.com/teppeis/multimaps/workflows/CI/badge.svg
[ci-url]: https://github.com/teppeis/multimaps/actions?query=workflow%3ACI
