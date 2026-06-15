"use strict"

const { rules: rulesRecommended } = require("./lib/configs/recommended")
const rules = require("./lib/rules")
const { name, version } = require("./package.json")

const plugin = {
    meta: { name, version },
    rules,
}

const recommended = {
    name: "@eslint-community/eslint-comments/recommended",
    plugins: {
        "@eslint-community/eslint-comments": plugin,
    },
    rules: rulesRecommended,
}

module.exports = {
    recommended,
}

module.exports.default = module.exports
