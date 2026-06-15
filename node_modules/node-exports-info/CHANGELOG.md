# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v1.6.0](https://github.com/inspect-js/node-exports-info/compare/v1.5.1...v1.6.0) - 2026-01-28

### Commits

- [New] add `getCategoryFlags` and `getCategoryInfo` APIs [`164024c`](https://github.com/inspect-js/node-exports-info/commit/164024c07e4612b8cfd470730b51f9ec78bdead2)
- [readme] use curly quotes in prose [`945e57a`](https://github.com/inspect-js/node-exports-info/commit/945e57a650d7d0ae085c84e11e493d939e77d05f)

## [v1.5.1](https://github.com/inspect-js/node-exports-info/compare/v1.5.0...v1.5.1) - 2026-01-28

### Commits

- [Types] add missing types changes from 547f4ef3f62e05032cb7b4d7e4f541eea380fcbf [`ad98746`](https://github.com/inspect-js/node-exports-info/commit/ad98746dcae60360813ea7fce8955415529b5408)

## [v1.5.0](https://github.com/inspect-js/node-exports-info/compare/v1.4.0...v1.5.0) - 2026-01-16

### Commits

- [New] add `node-addons` condition support [`fd11809`](https://github.com/inspect-js/node-exports-info/commit/fd118093e55e8fcb1b3b1c90779e277a6806bc73)
- [New] add `module-sync` condition support [`6cc5123`](https://github.com/inspect-js/node-exports-info/commit/6cc51230673a8846d5b1d2ec4124e35c9d6f077f)
- [New] add `subpath-imports-slash` category for `#/` subpath imports [`547f4ef`](https://github.com/inspect-js/node-exports-info/commit/547f4ef3f62e05032cb7b4d7e4f541eea380fcbf)

## [v1.4.0](https://github.com/inspect-js/node-exports-info/compare/v1.3.1...v1.4.0) - 2026-01-12

### Commits

- [Refactor] use loops instead of `array.prototype.find` [`d58884b`](https://github.com/inspect-js/node-exports-info/commit/d58884b03ce0ac49ba74f0ac923d5388f468af7c)
- [types] use shared config [`136778d`](https://github.com/inspect-js/node-exports-info/commit/136778db519a5b7e3b1ad13f40d71e4c05de196e)
- [Dev Deps] update `eslint` [`616920c`](https://github.com/inspect-js/node-exports-info/commit/616920cc40f5be64eaca8f02626d3543ae4816d3)
- [New] add type stripping, require(esm), JSON imports [`75b97f1`](https://github.com/inspect-js/node-exports-info/commit/75b97f1d7108207dadcfd3ab7010cd15ed2aebe1)
- [actions] split out node 10-20, and 20+ [`7e992d2`](https://github.com/inspect-js/node-exports-info/commit/7e992d25b4d144405f9fcd51d2ef80f0cd614dd3)
- [Dev Deps] update `@arethetypeswrong/cli`, `@ljharb/eslint-config`, `@types/object-inspect`, `auto-changelog`, `es-value-fixtures`, `object-inspect`, `tape` [`417745a`](https://github.com/inspect-js/node-exports-info/commit/417745a3186a03b1b2ddb26aa7c0d16fd59edb91)
- [Robustness] use `es-errors` [`c25eda7`](https://github.com/inspect-js/node-exports-info/commit/c25eda77ad517d7b01be662e1ce9b86974b49f87)
- [Dev Deps] update `@arethetypeswrong/cli`, `@ljharb/tsconfig`, `@types/tape`, `es-value-fixtures`, `for-each`, `object-inspect` [`84c5d1b`](https://github.com/inspect-js/node-exports-info/commit/84c5d1b8eb670b985b1ae25a32b198a61383f34d)
- [Fix] update the strips-types node ranges [`e6ef526`](https://github.com/inspect-js/node-exports-info/commit/e6ef52685f5d2c05b22e5bac03086b8a2b0836e0)
- [Dev Deps] update `@arethetypeswrong/cli`, `@ljharb/eslint-config`, `eslint`, `npmignore` [`f10c9d8`](https://github.com/inspect-js/node-exports-info/commit/f10c9d8373c6876872144ed33a9abadcdbc3265a)
- [readme] fix badges [`0dd9d62`](https://github.com/inspect-js/node-exports-info/commit/0dd9d624c17c135def20f0e43d095fd555640919)
- [Deps] update `array.prototype.flatmap`, `object.entries` [`140b885`](https://github.com/inspect-js/node-exports-info/commit/140b8852614b64c23444109377df4cbb41638647)
- [Deps] update `array.prototype.find`, `object.entries` [`0d87ad7`](https://github.com/inspect-js/node-exports-info/commit/0d87ad7fe6e58eda7424bffb311480b65e865af8)
- [Tests] replace `aud` with `npm audit` [`5d03f96`](https://github.com/inspect-js/node-exports-info/commit/5d03f964dc4e48b02a2ae53e7376488568115a97)
- [Tests] use `@arethetypeswrong/cli` [`5a2ef68`](https://github.com/inspect-js/node-exports-info/commit/5a2ef68cc53940701533240f2e251a502e00aaf1)
- [Dev Deps] update `@arethetypeswrong/cli` [`0a430bc`](https://github.com/inspect-js/node-exports-info/commit/0a430bc15e029d115ee6d6562a7c835ca9623f90)

## [v1.3.1](https://github.com/inspect-js/node-exports-info/compare/v1.3.0...v1.3.1) - 2024-02-26

### Commits

- add types [`c3449ed`](https://github.com/inspect-js/node-exports-info/commit/c3449edd1e3c0e1dd019c3c5ef9f075305577372)
- [actions] skip ls check on node &lt; 10; remove redundant finisher [`8a88b7b`](https://github.com/inspect-js/node-exports-info/commit/8a88b7b82a05787540541bd40dd92c4d73083e19)
- [actions] remove erroneous `none` permission [`9145df6`](https://github.com/inspect-js/node-exports-info/commit/9145df664d6ccbb49a812ccadb35ecad5957a6ba)
- [Dev Deps] update `tape` [`ff1f4de`](https://github.com/inspect-js/node-exports-info/commit/ff1f4ded536ea936a96c1c01f026768abc41ac27)

## [v1.3.0](https://github.com/inspect-js/node-exports-info/compare/v1.2.1...v1.3.0) - 2023-12-15

### Commits

- [New] add `isCategory` [`13b0f5f`](https://github.com/inspect-js/node-exports-info/commit/13b0f5f1ae7db4ddbbcc8a25f4acf671fffaf622)

## [v1.2.1](https://github.com/inspect-js/node-exports-info/compare/v1.2.0...v1.2.1) - 2023-12-15

### Commits

- [meta] use `npmignore` to autogenerate an npmignore file [`e79731c`](https://github.com/inspect-js/node-exports-info/commit/e79731c10ea60ddd06cc5d8ffe0acd2ac5ca051a)
- [actions] update rebase action to use reusable workflow [`20eab87`](https://github.com/inspect-js/node-exports-info/commit/20eab879a247e893c3566f5327a0e1b8978e0ccc)
- [Deps] update `array.prototype.find`, `array.prototype.flatmap`, `object.entries`, `semver` [`7f3bf1b`](https://github.com/inspect-js/node-exports-info/commit/7f3bf1bce617bab72f5091f150549fc344beb0a0)
- [Dev Deps] update `@ljharb/eslint-config`, `aud`, `npmignore`, `tape` [`a30b7b7`](https://github.com/inspect-js/node-exports-info/commit/a30b7b7880de4f2aa2f45537233bb5e30abc3169)
- [Dev Deps] update `@ljharb/eslint-config`, `aud`, `tape` [`1f262ad`](https://github.com/inspect-js/node-exports-info/commit/1f262ad99324825a8fd9b3ce5cf425f4a849a6c4)
- [Deps] update `array.prototype.find`, `array.prototype.flatmap` [`660e637`](https://github.com/inspect-js/node-exports-info/commit/660e637bf7a5cfbdf90e5ad174a437cf381c5c3d)
- [meta] add `safe-publish-latest` [`bcfb161`](https://github.com/inspect-js/node-exports-info/commit/bcfb161a37311a7791147addceda91ca9ef4a006)
- [Robustness] `ranges`: make it a null object [`5a6d476`](https://github.com/inspect-js/node-exports-info/commit/5a6d47631a6491ec7517b8a2ce3a7ba9ccece461)

## [v1.2.0](https://github.com/inspect-js/node-exports-info/compare/v1.1.3...v1.2.0) - 2022-04-08

### Commits

- Revert "[Tests] temporarily use actions instead of composable workflows" [`1d12795`](https://github.com/inspect-js/node-exports-info/commit/1d1279531112e422d1b67cad2bc267684ec0ca81)
- [New] `getConditionsForCategory`: add optional `moduleSystem` argument [`b4164bd`](https://github.com/inspect-js/node-exports-info/commit/b4164bde3658ec66c08319e411f01096939a734a)
- [actions] restrict permissions [`d0f58ef`](https://github.com/inspect-js/node-exports-info/commit/d0f58ef3696498a3030eb378ce0c98d32e8c7bba)
- [Dev Deps] update `tape` [`afaa392`](https://github.com/inspect-js/node-exports-info/commit/afaa3928208f93f308e1045eb9c5e8e50cea4e18)

## [v1.1.3](https://github.com/inspect-js/node-exports-info/compare/v1.1.2...v1.1.3) - 2022-03-24

### Commits

- [Fix] `node v13.13 also has broken dir-slash [`cc9f891`](https://github.com/inspect-js/node-exports-info/commit/cc9f891f8679a1e4b1063d2d91546b72f82be011)
- [meta] add missing `version` config [`6a7f8c6`](https://github.com/inspect-js/node-exports-info/commit/6a7f8c629d9fb41315c3cea2c514d0398c6be2c7)

## [v1.1.2](https://github.com/inspect-js/node-exports-info/compare/v1.1.1...v1.1.2) - 2022-03-22

### Commits

- [Fix] turns out all `patterns` nodes have a broken dir-slash [`3e8310b`](https://github.com/inspect-js/node-exports-info/commit/3e8310b79496de9d177487c3b5d199cd66630d9d)

## [v1.1.1](https://github.com/inspect-js/node-exports-info/compare/v1.1.0...v1.1.1) - 2022-03-21

### Commits

- [Fix] correct category version ranges [`e98260d`](https://github.com/inspect-js/node-exports-info/commit/e98260dc78a7e969c4fa0d868934066865f344e2)

## [v1.1.0](https://github.com/inspect-js/node-exports-info/compare/v1.0.2...v1.1.0) - 2022-03-21

### Commits

- [New] add three new categories: [`a549cb8`](https://github.com/inspect-js/node-exports-info/commit/a549cb884e8d6a990fdcdd5eb9b10e922a24c89c)

## [v1.0.2](https://github.com/inspect-js/node-exports-info/compare/v1.0.1...v1.0.2) - 2022-03-21

### Commits

- [Fix] fix sort ordering of range pairs [`48a6865`](https://github.com/inspect-js/node-exports-info/commit/48a68659e890d4331ede9c971709ca03e5ab3b9a)

## [v1.0.1](https://github.com/inspect-js/node-exports-info/compare/v1.0.0...v1.0.1) - 2022-03-21

### Commits

- [meta] do not publish workflow files [`44a1fe8`](https://github.com/inspect-js/node-exports-info/commit/44a1fe82cffc4453d8bc5171d70284b205db7bcc)
- read me [`99e4edf`](https://github.com/inspect-js/node-exports-info/commit/99e4edf1b245b8c58b8854c7596da5007e3f887e)
- [Test] add tests [`462bd2b`](https://github.com/inspect-js/node-exports-info/commit/462bd2b0a8e0147f308f93885f30e1d255e1746e)

## v1.0.0 - 2022-03-20

### Commits

- initial implementation and tests [`633f2bc`](https://github.com/inspect-js/node-exports-info/commit/633f2bcfc4a939c3095ea1c6cc08d426baa1c726)
- Initial commit [`bef50ef`](https://github.com/inspect-js/node-exports-info/commit/bef50ef02aabd8a50d8841d665106aeb6097248f)
- [Tests] temporarily use actions instead of composable workflows [`436fbbf`](https://github.com/inspect-js/node-exports-info/commit/436fbbf9612f0d661cc66b7a73247015eccbef13)
- `npm init` [`0c85774`](https://github.com/inspect-js/node-exports-info/commit/0c8577490640779d2881dbd02d1a8dca7c9951a5)
- Only apps should have lockfiles [`28d9d61`](https://github.com/inspect-js/node-exports-info/commit/28d9d6160d10855cbf29bb1e4751260b87735d34)
