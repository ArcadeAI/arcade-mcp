# sh-syntax

[![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/un-ts/sh-syntax/ci.yml?branch=main)](https://github.com/un-ts/sh-syntax/actions/workflows/ci.yml?query=branch%3Amain)
[![Codecov](https://img.shields.io/codecov/c/github/un-ts/sh-syntax.svg)](https://codecov.io/gh/un-ts/sh-syntax)
[![type-coverage](https://img.shields.io/badge/dynamic/json.svg?label=type-coverage&prefix=%E2%89%A5&suffix=%&query=$.typeCoverage.atLeast&uri=https%3A%2F%2Fraw.githubusercontent.com%2Fun-ts%2Fsh-syntax%2Fmain%2Fpackage.json)](https://github.com/plantain-00/type-coverage)
[![CodeRabbit Pull Request Reviews](https://img.shields.io/coderabbit/prs/github/un-ts/sh-syntax)](https://coderabbit.ai)
[![npm](https://img.shields.io/npm/v/sh-syntax.svg)](https://www.npmjs.com/package/sh-syntax)
[![GitHub Release](https://img.shields.io/github/release/un-ts/sh-syntax)](https://github.com/un-ts/sh-syntax/releases)

[![Conventional Commits](https://img.shields.io/badge/conventional%20commits-1.0.0-yellow.svg)](https://conventionalcommits.org)
[![Renovate enabled](https://img.shields.io/badge/renovate-enabled-brightgreen.svg)](https://renovatebot.com)
[![JavaScript Style Guide](https://img.shields.io/badge/code_style-standard-brightgreen.svg)](https://standardjs.com)
[![Code Style: Prettier](https://img.shields.io/badge/code_style-prettier-ff69b4.svg)](https://github.com/prettier/prettier)
[![changesets](https://img.shields.io/badge/maintained%20with-changesets-176de3.svg)](https://github.com/changesets/changesets)

A WASM shell parser and formatter with bash support, based on [mvdan/sh](https://github.com/mvdan/sh)

## TOC <!-- omit in toc -->

- [Usage](#usage)
  - [Install](#install)
  - [API](#api)
    - [node](#node)
    - [browser](#browser)
- [Benchmark](#benchmark)
- [Sponsors](#sponsors)
- [Backers](#backers)
- [Changelog](#changelog)
- [License](#license)

## Usage

### Install

```sh
# yarn
yarn add sh-syntax

# npm
npm i sh-syntax
```

### API

#### node

```js
import { parse, print } from 'sh-syntax'

const text = "echo 'Hello World!'"
const ast = await parse(text)
const newText = await print(ast, {
  // `originalText` is required for now, hope we will find better solution later
  originalText: text,
})
```

#### browser

```js
import { getProcessor } from 'sh-syntax'

// choose your own way to load the WASM file

// with `fetch`
const processor = getProcessor(() =>
  fetch('http://cdn.jsdelivr.net/npm/sh-syntax@latest/main.wasm'),
)

// with `wasm?init` via `vite`
import initWasm from 'sh-syntax/wasm?init'
const processor = getProcessor(initWasm)

const parse = (text, options) => processor(text, options)

const print = (textOrAst, options) => {
  if (typeof textOrAst === 'string') {
    return processor(textOrAst, {
      ...options,
      print: true,
    })
  }
  return processor(textOrAst, options)
}

// just like node again
const text = "echo 'Hello World!'"
const ast = await parse(text)
const newText = await print(ast, { originalText: text })
```

## Benchmark

```console
clk: ~2.81 GHz
cpu: Apple M1 Max
runtime: node 18.20.8 (arm64-darwin)

benchmark                   avg (min … max) p75 / p99    (min … top 1%)
------------------------------------------- -------------------------------
sh-syntax                     18.33 ms/iter  18.56 ms   ▃        ▃█
                      (17.48 ms … 20.83 ms)  19.09 ms ▂▂█    ▂   ██▂  ▂ ▂
                    ( 28.52 kb …   9.82 mb) 890.46 kb ███▆▆▁▁█▁▁▆███▁▆█▁█▆▆
                  5.07 ipc (  1.22% stalls)  99.36% L1 data cache
         56.96M cycles 288.57M instructions  39.27% retired LD/ST (113.32M)

sh-syntax (synckit)           18.38 ms/iter  18.82 ms ▂▂▂           ▂▂ █▂
                      (17.63 ms … 19.06 ms)  19.04 ms ███▅          ██ ██▅▅
                    (291.31 kb … 312.45 kb) 292.09 kb ████▇▇▇▇▁▁▁▁▇▁██▇████
                  1.11 ipc ( 11.51% stalls)  40.34% L1 data cache
        434.86k cycles 484.78k instructions  19.58% retired LD/ST ( 94.92k)

mvdan-sh                      79.47 ms/iter  78.95 ms  █
                     (71.22 ms … 126.09 ms)  80.84 ms ▅█ ▅▅▅    ▅    ▅▅▅  ▅
                    (  8.18 mb …   9.70 mb)   8.83 mb ██▁███▁▁▁▁█▁▁▁▁███▁▁█
                  5.18 ipc (  1.05% stalls)  99.04% L1 data cache
        249.41M cycles   1.29G instructions  34.41% retired LD/ST (444.42M)

summary
  sh-syntax
   1x faster than sh-syntax (synckit)
   4.34x faster than mvdan-sh
```

See [benchmark](./benchmark/benchmark.txt) for more details.

You can try it with running `node benchmark` by yourself. [Here](./benchmark/index.js) is the benchmark source code.

## Sponsors and Backers

[![Sponsors and Backers](https://raw.githubusercontent.com/1stG/static/master/sponsors.svg)](https://github.com/sponsors/JounQin)

### Sponsors

| 1stG                                                                                                                   | RxTS                                                                                                                   | UnTS                                                                                                                   |
| ---------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| [![1stG Open Collective sponsors](https://opencollective.com/1stG/organizations.svg)](https://opencollective.com/1stG) | [![RxTS Open Collective sponsors](https://opencollective.com/rxts/organizations.svg)](https://opencollective.com/rxts) | [![UnTS Open Collective sponsors](https://opencollective.com/unts/organizations.svg)](https://opencollective.com/unts) |

### Backers

| 1stG                                                                                                                | RxTS                                                                                                                | UnTS                                                                                                                |
| ------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| [![1stG Open Collective backers](https://opencollective.com/1stG/individuals.svg)](https://opencollective.com/1stG) | [![RxTS Open Collective backers](https://opencollective.com/rxts/individuals.svg)](https://opencollective.com/rxts) | [![UnTS Open Collective backers](https://opencollective.com/unts/individuals.svg)](https://opencollective.com/unts) |

## Changelog

Detailed changes for each release are documented in [CHANGELOG.md](./CHANGELOG.md).

## License

[MIT][] © [JounQin][]@[1stG.me][]

[1stG.me]: https://www.1stg.me
[JounQin]: https://github.com/JounQin
[MIT]: http://opensource.org/licenses/MIT
