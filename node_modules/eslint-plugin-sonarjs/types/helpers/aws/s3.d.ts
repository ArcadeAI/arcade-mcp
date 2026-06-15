import type { Rule } from 'eslint';
import type estree from 'estree';
import { type IssueLocation } from '../location.js';
import type { RulesMeta } from '@eslint/core';
/**
 * A rule template for AWS S3 Buckets
 *
 * The rule template allows to detect sensitive configuration passed on
 * the invocation of S3 Bucket's constructor from AWS CDK:
 *
 * ```new s3.Bucket(...)```
 *
 * @param callback the callback invoked on visiting S3 Bucket's instantiation
 * @param meta the instantiated rule metadata
 * @returns the instantiated rule definition
 */
export declare function S3BucketTemplate(callback: (bucketConstructor: estree.NewExpression, context: Rule.RuleContext) => void, meta?: RulesMeta): Rule.RuleModule;
/**
 * Detects S3 Bucket's constructor invocation from 'aws-cdk-lib/aws-s3':
 *
 * const s3 = require('aws-cdk-lib/aws-s3');
 * new s3.Bucket();
 */
export declare function isS3BucketConstructor(context: Rule.RuleContext, node: estree.NewExpression): boolean;
/**
 * Detects S3 BucketDeployment's constructor invocation from 'aws-cdk-lib/aws-s3-deployment':
 *
 * const s3 = require('aws-cdk-lib/aws-s3-deployment');
 * new s3.BucketDeployment();
 */
export declare function isS3BucketDeploymentConstructor(context: Rule.RuleContext, node: estree.NewExpression): boolean;
/**
 * Extracts a property from the configuration argument of S3 Bucket's constructor
 *
 * ```
 * new s3.Bucket(_, _, { // config
 *  key1: value1,
 *  ...
 *  keyN: valueN
 * });
 * ```
 *
 * @param context the rule context
 * @param bucket the invocation of S3 Bucket's constructor
 * @param key the key of the property to extract
 * @returns the extracted property
 */
export declare function getBucketProperty(context: Rule.RuleContext, bucket: estree.NewExpression, key: string): estree.Property | null | undefined;
/**
 * Finds the propagated setting of a sensitive property
 */
export declare function findPropagatedSetting(sensitiveProperty: estree.Property, propagatedValue: estree.Node): IssueLocation | undefined;
