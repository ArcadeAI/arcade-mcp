import type CssParseError from './CssParseError';
import type Position from './CssPosition';

export enum CssTypes {
  stylesheet = 'stylesheet',
  rule = 'rule',
  declaration = 'declaration',
  comment = 'comment',
  atRule = 'at-rule',
  container = 'container',
  charset = 'charset',
  counterStyle = 'counter-style',
  document = 'document',
  customMedia = 'custom-media',
  fontFace = 'font-face',
  fontFeatureValues = 'font-feature-values',
  host = 'host',
  import = 'import',
  keyframes = 'keyframes',
  keyframe = 'keyframe',
  layer = 'layer',
  media = 'media',
  namespace = 'namespace',
  page = 'page',
  pageMarginBox = 'page-margin-box',
  positionTry = 'position-try',
  property = 'property',
  scope = 'scope',
  startingStyle = 'starting-style',
  supports = 'supports',
  viewTransition = 'view-transition',
}

export type CssCommonAST = {
  type: CssTypes;
};

export type CssCommonPositionAST = CssCommonAST & {
  position?: Position;
  parent?: unknown;
};

export type CssStylesheetAST = CssCommonAST & {
  type: CssTypes.stylesheet;
  stylesheet: {
    source?: string;
    rules: Array<CssAtRuleAST>;
    parsingErrors?: Array<CssParseError>;
  };
};

export type CssRuleAST = CssCommonPositionAST & {
  type: CssTypes.rule;
  selectors: Array<string>;
  declarations: Array<CssDeclarationAST | CssCommentAST | CssAtRuleAST>;
};

export type CssDeclarationAST = CssCommonPositionAST & {
  type: CssTypes.declaration;
  property: string;
  value: string;
};

export type CssCommentAST = CssCommonPositionAST & {
  type: CssTypes.comment;
  comment: string;
};
export type CssContainerAST = CssCommonPositionAST & {
  type: CssTypes.container;
  container: string;
  rules: Array<CssAtRuleAST | CssDeclarationAST>;
};

export type CssCharsetAST = CssCommonPositionAST & {
  type: CssTypes.charset;
  charset: string;
};
export type CssCustomMediaAST = CssCommonPositionAST & {
  type: CssTypes.customMedia;
  name: string;
  media: string;
};
export type CssDocumentAST = CssCommonPositionAST & {
  type: CssTypes.document;
  document: string;
  vendor?: string;
  rules: Array<CssAtRuleAST | CssDeclarationAST>;
};
export type CssFontFaceAST = CssCommonPositionAST & {
  type: CssTypes.fontFace;
  declarations: Array<CssDeclarationAST | CssCommentAST>;
};
export type CssHostAST = CssCommonPositionAST & {
  type: CssTypes.host;
  rules: Array<CssAtRuleAST | CssDeclarationAST>;
};
export type CssImportAST = CssCommonPositionAST & {
  type: CssTypes.import;
  import: string;
};
export type CssKeyframesAST = CssCommonPositionAST & {
  type: CssTypes.keyframes;
  name: string;
  vendor?: string;
  keyframes: Array<CssKeyframeAST | CssCommentAST>;
};
export type CssKeyframeAST = CssCommonPositionAST & {
  type: CssTypes.keyframe;
  values: Array<string>;
  declarations: Array<CssDeclarationAST | CssCommentAST>;
};
export type CssLayerAST = CssCommonPositionAST & {
  type: CssTypes.layer;
  layer: string;
  rules?: Array<CssAtRuleAST | CssDeclarationAST>;
};
export type CssMediaAST = CssCommonPositionAST & {
  type: CssTypes.media;
  media: string;
  rules: Array<CssAtRuleAST | CssDeclarationAST>;
};
export type CssNamespaceAST = CssCommonPositionAST & {
  type: CssTypes.namespace;
  namespace: string;
};
export type CssPageAST = CssCommonPositionAST & {
  type: CssTypes.page;
  selectors: Array<string>;
  declarations: Array<CssDeclarationAST | CssCommentAST | CssAtRuleAST>;
};
export type CssSupportsAST = CssCommonPositionAST & {
  type: CssTypes.supports;
  supports: string;
  rules: Array<CssAtRuleAST | CssDeclarationAST>;
};

export type CssStartingStyleAST = CssCommonPositionAST & {
  type: CssTypes.startingStyle;
  rules: Array<CssAtRuleAST | CssDeclarationAST>;
};

export type CssCounterStyleAST = CssCommonPositionAST & {
  type: CssTypes.counterStyle;
  name: string;
  declarations: Array<CssDeclarationAST | CssCommentAST>;
};
export type CssFontFeatureValuesAST = CssCommonPositionAST & {
  type: CssTypes.fontFeatureValues;
  fontFamily: string;
  rules: Array<CssAtRuleAST | CssDeclarationAST>;
};
export type CssPositionTryAST = CssCommonPositionAST & {
  type: CssTypes.positionTry;
  name: string;
  declarations: Array<CssDeclarationAST | CssCommentAST>;
};
export type CssPropertyAST = CssCommonPositionAST & {
  type: CssTypes.property;
  name: string;
  declarations: Array<CssDeclarationAST | CssCommentAST>;
};
export type CssScopeAST = CssCommonPositionAST & {
  type: CssTypes.scope;
  scope: string;
  rules: Array<CssAtRuleAST | CssDeclarationAST>;
};
export type CssViewTransitionAST = CssCommonPositionAST & {
  type: CssTypes.viewTransition;
  declarations: Array<CssDeclarationAST | CssCommentAST>;
};
export type CssPageMarginBoxAST = CssCommonPositionAST & {
  type: CssTypes.pageMarginBox;
  name: string;
  declarations: Array<CssDeclarationAST | CssCommentAST>;
};
export type CssGenericAtRuleAST = CssCommonPositionAST & {
  type: CssTypes.atRule;
  name: string;
  prelude: string;
  rules?: Array<CssAtRuleAST | CssDeclarationAST>;
};

export type CssAtRuleAST =
  | CssRuleAST
  | CssCommentAST
  | CssContainerAST
  | CssCharsetAST
  | CssCounterStyleAST
  | CssCustomMediaAST
  | CssDocumentAST
  | CssFontFaceAST
  | CssFontFeatureValuesAST
  | CssHostAST
  | CssImportAST
  | CssKeyframesAST
  | CssLayerAST
  | CssMediaAST
  | CssNamespaceAST
  | CssPageAST
  | CssPageMarginBoxAST
  | CssPositionTryAST
  | CssPropertyAST
  | CssScopeAST
  | CssSupportsAST
  | CssStartingStyleAST
  | CssViewTransitionAST
  | CssGenericAtRuleAST;

export type CssAllNodesAST =
  | CssAtRuleAST
  | CssStylesheetAST
  | CssDeclarationAST
  | CssKeyframeAST;
