# jsx-ast-utils-x

[![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/eslinter/jsx-ast-utils-x/ci.yml?branch=main)](https://github.com/eslinter/jsx-ast-utils-x/actions/workflows/ci.yml?query=branch%3Amain)
[![Codecov](https://img.shields.io/codecov/c/github/eslinter/jsx-ast-utils-x.svg)](https://codecov.io/gh/eslinter/jsx-ast-utils-x)
[![type-coverage](https://img.shields.io/badge/dynamic/json.svg?label=type-coverage&prefix=%E2%89%A5&suffix=%&query=$.typeCoverage.atLeast&uri=https%3A%2F%2Fraw.githubusercontent.com%2Feslinter%2Fjsx-ast-utils-x%2Fmain%2Fpackage.json)](https://github.com/plantain-00/type-coverage)
[![CodeRabbit Pull Request Reviews](https://img.shields.io/coderabbit/prs/github/eslinter/jsx-ast-utils-x)](https://coderabbit.ai)
[![npm](https://img.shields.io/npm/v/jsx-ast-utils-x.svg)](https://www.npmjs.com/package/jsx-ast-utils-x)
[![GitHub Release](https://img.shields.io/github/release/eslinter/jsx-ast-utils-x)](https://github.com/eslinter/jsx-ast-utils-x/releases)

[![Conventional Commits](https://img.shields.io/badge/conventional%20commits-1.0.0-yellow.svg)](https://conventionalcommits.org)
[![Renovate enabled](https://img.shields.io/badge/renovate-enabled-brightgreen.svg)](https://renovatebot.com)
[![JavaScript Style Guide](https://img.shields.io/badge/code_style-standard-brightgreen.svg)](https://standardjs.com)
[![Code Style: Prettier](https://img.shields.io/badge/code_style-prettier-ff69b4.svg)](https://github.com/prettier/prettier)
[![changesets](https://img.shields.io/badge/maintained%20with-changesets-176de3.svg)](https://github.com/changesets/changesets)

AST utility module for statically analyzing JSX.

## TOC <!-- omit in toc -->

- [Installation](#installation)
- [Usage](#usage)
  - [ESLint example](#eslint-example)
- [API](#api)
  - [AST Resources](#ast-resources)
  - [hasProp](#hasprop)
    - [Props](#props)
    - [Prop](#prop)
    - [Options](#options)
  - [hasAnyProp](#hasanyprop)
    - [Props](#props-1)
    - [Prop](#prop-1)
    - [Options](#options-1)
  - [hasEveryProp](#haseveryprop)
    - [Props](#props-2)
    - [Prop](#prop-2)
    - [Options](#options-2)
  - [getProp](#getprop)
    - [Props](#props-3)
    - [Prop](#prop-3)
    - [Options](#options-3)
  - [elementType](#elementtype)
    - [Node](#node)
  - [getPropValue](#getpropvalue)
    - [Prop](#prop-4)
  - [getLiteralPropValue](#getliteralpropvalue)
    - [Prop](#prop-5)
  - [propName](#propname)
    - [Prop](#prop-6)
  - [eventHandlers](#eventhandlers)
    - [eventHandlersByType](#eventhandlersbytype)
- [Sponsors and Backers](#sponsors-and-backers)
  - [Sponsors](#sponsors)
  - [Backers](#backers)
- [Changelog](#changelog)
- [License](#license)

## Installation

```sh
# npm
npm i jsx-ast-utils-x --save

# yarn
yarn add jsx-ast-utils-x

# pnpm
pnpm add jsx-ast-utils-x

# bun
bun add jsx-ast-utils-x
```

## Usage

This is a utility module to evaluate AST objects for JSX syntax. This can be super useful when writing linting rules for JSX code. It was originally in the code for [eslint-plugin-jsx-a11y](https://github.com/eslinter/eslint-plugin-jsx-a11y), however I thought it could be useful to be extracted and maintained separately so **you** could write new interesting rules to statically analyze JSX.

### ESLint example

```js
import { hasProp } from 'jsx-ast-utils-x';
// OR: var hasProp = require('jsx-ast-utils-x').hasProp;
// OR: const hasProp = require('jsx-ast-utils-x/hasProp');
// OR: import hasProp from 'jsx-ast-utils-x/hasProp';

module.exports = context => ({
  JSXOpeningElement: node => {
    const onChange = hasProp(node.attributes, 'onChange');

    if (onChange) {
      context.report({
        node,
        message: `No onChange!`,
      });
    }
  },
});
```

## API

### AST Resources

1. [JSX spec](https://github.com/facebook/jsx/blob/master/AST.md)
2. [JS spec](https://github.com/estree/estree/blob/master/spec.md)

### hasProp

```js
hasProp(props, prop, options);
```

Returns boolean indicating whether an prop exists as an attribute on a JSX element node.

#### Props

Object - The attributes on the visited node. (Usually `node.attributes`).

#### Prop

String - A string representation of the prop you want to check for existence.

#### Options

Object - An object representing options for existence checking

1. `ignoreCase` - automatically set to `true`.
2. `spreadStrict` - automatically set to `true`. This means if spread operator exists in
   props, it will assume the prop you are looking for is not in the spread.
   Example: `<div {...props} />` looking for specific prop here will return false if `spreadStrict` is `true`.

<hr />

### hasAnyProp

```js
hasAnyProp(props, prop, options);
```

Returns a boolean indicating if **any** of props in `prop` argument exist on the node.

#### Props

Object - The attributes on the visited node. (Usually `node.attributes`).

#### Prop

Array<String> - An array of strings representing the props you want to check for existence.

#### Options

Object - An object representing options for existence checking

1. `ignoreCase` - automatically set to `true`.
2. `spreadStrict` - automatically set to `true`. This means if spread operator exists in
   props, it will assume the prop you are looking for is not in the spread.
   Example: `<div {...props} />` looking for specific prop here will return false if `spreadStrict` is `true`.

<hr />

### hasEveryProp

```js
hasEveryProp(props, prop, options);
```

Returns a boolean indicating if **all** of props in `prop` argument exist on the node.

#### Props

Object - The attributes on the visited node. (Usually `node.attributes`).

#### Prop

Array<String> - An array of strings representing the props you want to check for existence.

#### Options

Object - An object representing options for existence checking

1.  `ignoreCase` - automatically set to `true`.
2.  `spreadStrict` - automatically set to `true`. This means if spread operator exists in
    props, it will assume the prop you are looking for is not in the spread.
    Example: `<div {...props} />` looking for specific prop here will return false if `spreadStrict` is `true`.

<hr />

### getProp

```js
getProp(props, prop, options);
```

Returns the JSXAttribute itself or undefined, indicating the prop is not present on the JSXOpeningElement.

#### Props

Object - The attributes on the visited node. (Usually `node.attributes`).

#### Prop

String - A string representation of the prop you want to check for existence.

#### Options

Object - An object representing options for existence checking

1. `ignoreCase` - automatically set to `true`.

<hr />

### elementType

```js
elementType(node);
```

Returns the tagName associated with a JSXElement.

#### Node

Object - The visited JSXElement node object.

<hr />

### getPropValue

```js
getPropValue(prop);
```

Returns the value of a given attribute. Different types of attributes have their associated values in different properties on the object.

This function should return the most _closely_ associated value with the intention of the JSX.

#### Prop

Object - The JSXAttribute collected by AST parser.

<hr />

### getLiteralPropValue

```js
getLiteralPropValue(prop);
```

Returns the value of a given attribute. Different types of attributes have their associated values in different properties on the object.

This function should return a value only if we can extract a literal value from its attribute (i.e. values that have generic types in JavaScript - strings, numbers, booleans, etc.)

#### Prop

Object - The JSXAttribute collected by AST parser.

<hr />

### propName

```js
propName(prop);
```

Returns the name associated with a JSXAttribute. For example, given `<div foo="bar" />` and the JSXAttribute for `foo`, this will return the string `"foo"`.

#### Prop

Object - The JSXAttribute collected by AST parser.

<hr />

### eventHandlers

```js
console.log(eventHandlers);
/*
[
  'onCopy',
  'onCut',
  'onPaste',
  'onCompositionEnd',
  'onCompositionStart',
  'onCompositionUpdate',
  'onKeyDown',
  'onKeyPress',
  'onKeyUp',
  'onFocus',
  'onBlur',
  'onChange',
  'onInput',
  'onSubmit',
  'onClick',
  'onContextMenu',
  'onDblClick',
  'onDoubleClick',
  'onDrag',
  'onDragEnd',
  'onDragEnter',
  'onDragExit',
  'onDragLeave',
  'onDragOver',
  'onDragStart',
  'onDrop',
  'onMouseDown',
  'onMouseEnter',
  'onMouseLeave',
  'onMouseMove',
  'onMouseOut',
  'onMouseOver',
  'onMouseUp',
  'onSelect',
  'onTouchCancel',
  'onTouchEnd',
  'onTouchMove',
  'onTouchStart',
  'onScroll',
  'onWheel',
  'onAbort',
  'onCanPlay',
  'onCanPlayThrough',
  'onDurationChange',
  'onEmptied',
  'onEncrypted',
  'onEnded',
  'onError',
  'onLoadedData',
  'onLoadedMetadata',
  'onLoadStart',
  'onPause',
  'onPlay',
  'onPlaying',
  'onProgress',
  'onRateChange',
  'onSeeked',
  'onSeeking',
  'onStalled',
  'onSuspend',
  'onTimeUpdate',
  'onVolumeChange',
  'onWaiting',
  'onLoad',
  'onError',
  'onAnimationStart',
  'onAnimationEnd',
  'onAnimationIteration',
  'onTransitionEnd',
]
*/
```

Contains a flat list of common event handler props used in JSX to attach behaviors
to DOM events.

#### eventHandlersByType

The same list as `eventHandlers`, grouped into types.

```js
console.log(eventHandlersByType);
/*
{
  clipboard: [ 'onCopy', 'onCut', 'onPaste' ],
  composition: [ 'onCompositionEnd', 'onCompositionStart', 'onCompositionUpdate' ],
  keyboard: [ 'onKeyDown', 'onKeyPress', 'onKeyUp' ],
  focus: [ 'onFocus', 'onBlur' ],
  form: [ 'onChange', 'onInput', 'onSubmit' ],
  mouse: [ 'onClick', 'onContextMenu', 'onDblClick', 'onDoubleClick', 'onDrag', 'onDragEnd', 'onDragEnter', 'onDragExit', 'onDragLeave', 'onDragOver', 'onDragStart', 'onDrop', 'onMouseDown', 'onMouseEnter', 'onMouseLeave', 'onMouseMove', 'onMouseOut', 'onMouseOver', 'onMouseUp' ],
  selection: [ 'onSelect' ],
  touch: [ 'onTouchCancel', 'onTouchEnd', 'onTouchMove', 'onTouchStart' ],
  ui: [ 'onScroll' ],
  wheel: [ 'onWheel' ],
  media: [ 'onAbort', 'onCanPlay', 'onCanPlayThrough', 'onDurationChange', 'onEmptied', 'onEncrypted', 'onEnded', 'onError', 'onLoadedData', 'onLoadedMetadata', 'onLoadStart', 'onPause', 'onPlay', 'onPlaying', 'onProgress', 'onRateChange', 'onSeeked', 'onSeeking', 'onStalled', 'onSuspend', 'onTimeUpdate', 'onVolumeChange', 'onWaiting' ],
  image: [ 'onLoad', 'onError' ],
  animation: [ 'onAnimationStart', 'onAnimationEnd', 'onAnimationIteration' ],
  transition: [ 'onTransitionEnd' ],
}
*/
```

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

[1stG.me]: https://www.1stG.me
[JounQin]: https://github.com/JounQin
[MIT]: http://opensource.org/licenses/MIT
