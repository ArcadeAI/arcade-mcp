"use strict";
/*
 * SonarQube JavaScript Plugin
 * Copyright (C) SonarSource Sàrl
 * mailto:info AT sonarsource DOT com
 *
 * You can redistribute and/or modify this program under the terms of
 * the Sonar Source-Available License Version 1, as published by SonarSource Sàrl.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
 * See the Sonar Source-Available License for more details.
 *
 * You should have received a copy of the Sonar Source-Available License
 * along with this program; if not, see https://sonarsource.com/license/ssal/
 */
// https://sonarsource.github.io/rspec/#/rspec/S2077/javascript
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.rule = void 0;
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const module_js_1 = require("../helpers/module.js");
const module_ts_js_1 = require("../helpers/module-ts.js");
const ast_js_1 = require("../helpers/ast.js");
const parser_services_js_1 = require("../helpers/parser-services.js");
const meta = __importStar(require("./generated-meta.js"));
const sqlQuerySignatures = new Set([
    'pg.Client.query',
    'pg.Pool.query',
    'mysql.createConnection.query',
    'mysql.createPool.query',
    'mysql.createPoolCluster.query',
    'mysql2.createConnection.query',
    'mysql2.createPool.query',
    'mysql2.createPoolCluster.query',
    'sequelize.Sequelize.query', // Sequelize is typically destructured: const { Sequelize } = require('sequelize')
    'sqlite3.Database.run',
    'sqlite3.Database.get',
    'sqlite3.Database.all',
    'sqlite3.Database.each',
    'sqlite3.Database.exec',
    'better-sqlite3.exec',
    'better-sqlite3.prepare',
    'mssql.ConnectionPool.query',
    'mssql.Request.query',
    'mssql.Request.batch',
    'mssql.Request.execute',
    'mysql2.createConnection.execute',
    'oracledb.getConnection.execute',
    'oracledb.getConnection.executeMany',
    'oracledb.getConnection.queryStream',
    'pg-promise.any',
    'pg-promise.each',
    'pg-promise.func',
    'pg-promise.many',
    'pg-promise.manyOrNone',
    'pg-promise.map',
    'pg-promise.multi',
    'pg-promise.multiResult',
    'pg-promise.none',
    'pg-promise.one',
    'pg-promise.oneOrNone',
    'pg-promise.proc',
    'pg-promise.query',
    'pg-promise.result',
    'knex.raw',
    'knex.whereRaw',
    'knex.havingRaw',
    'knex.groupByRaw',
    'knex.orderByRaw',
    'knex.joinRaw',
    'typeorm.createConnection.query',
    'typeorm.getConnection.query',
    'typeorm.getManager.query',
    'typeorm.getRepository.query',
]);
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            safeQuery: `Make sure that executing SQL queries is safe here.`,
        },
    }),
    create(context) {
        const services = context.sourceCode.parserServices;
        const hasTypeInformation = (0, parser_services_js_1.isRequiredParserServices)(services);
        return {
            CallExpression(node) {
                let fqn = null;
                if (hasTypeInformation) {
                    const tsNode = services.esTreeNodeToTSNodeMap.get(node);
                    fqn = (0, module_ts_js_1.getFullyQualifiedNameTS)(services, tsNode);
                }
                else {
                    fqn = (0, module_js_1.getFullyQualifiedName)(context, node.callee);
                }
                if (fqn && sqlQuerySignatures.has(fqn) && isQuestionable(node.arguments[0])) {
                    context.report({
                        messageId: 'safeQuery',
                        node: node.callee,
                    });
                }
            },
        };
    },
};
function isQuestionable(sqlQuery) {
    if (!sqlQuery) {
        return false;
    }
    if (isTemplateWithVar(sqlQuery)) {
        return true;
    }
    if (isConcatenation(sqlQuery)) {
        return isVariableConcat(sqlQuery);
    }
    return (sqlQuery.type === 'CallExpression' && (0, ast_js_1.isMemberWithProperty)(sqlQuery.callee, 'concat', 'replace'));
}
function isVariableConcat(node) {
    const { left, right } = node;
    if (!isHardcodedLiteral(right)) {
        return true;
    }
    if (isConcatenation(left)) {
        return isVariableConcat(left);
    }
    return !isHardcodedLiteral(left);
}
function isTemplateWithVar(node) {
    return node.type === 'TemplateLiteral' && node.expressions.length !== 0;
}
function isTemplateWithoutVar(node) {
    return node.type === 'TemplateLiteral' && node.expressions.length === 0;
}
function isConcatenation(node) {
    return node.type === 'BinaryExpression' && node.operator === '+';
}
function isHardcodedLiteral(node) {
    return node.type === 'Literal' || isTemplateWithoutVar(node);
}
