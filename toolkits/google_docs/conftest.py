import pytest


@pytest.fixture
def sample_document_and_expected_formats():
    document = {
        "title": "The Birth of Machine Experience Engineering",
        "documentId": "1234567890",
        "body": {
            "content": [
                {
                    "endIndex": 1,
                    "sectionBreak": {
                        "sectionStyle": {
                            "columnSeparatorStyle": "NONE",
                            "contentDirection": "LEFT_TO_RIGHT",
                            "sectionType": "CONTINUOUS",
                        }
                    },
                },
                {
                    "startIndex": 1,
                    "endIndex": 45,
                    "paragraph": {
                        "elements": [
                            {
                                "endIndex": 45,
                                "startIndex": 1,
                                "textRun": {
                                    "content": "The Birth of Machine Experience Engineering\n",
                                    "textStyle": {
                                        "bold": True,
                                        "fontSize": {"magnitude": 23, "unit": "PT"},
                                    },
                                },
                            }
                        ],
                        "paragraphStyle": {
                            "direction": "LEFT_TO_RIGHT",
                            "headingId": "h.wwd7ec37bh6k",
                            "keepLinesTogether": False,
                            "keepWithNext": False,
                            "namedStyleType": "HEADING_1",
                            "spaceAbove": {"magnitude": 24, "unit": "PT"},
                        },
                    },
                },
                {
                    "startIndex": 45,
                    "endIndex": 46,
                    "paragraph": {
                        "elements": [
                            {
                                "startIndex": 304,
                                "endIndex": 305,
                                "inlineObjectElement": {
                                    "inlineObjectId": "kix.2s5wy5oiaf79",
                                    "textStyle": {},
                                },
                            },
                            {
                                "endIndex": 46,
                                "startIndex": 45,
                                "textRun": {"content": "\n", "textStyle": {}},
                            },
                        ],
                        "paragraphStyle": {
                            "direction": "LEFT_TO_RIGHT",
                            "namedStyleType": "NORMAL_TEXT",
                            "spaceAbove": {"magnitude": 12, "unit": "PT"},
                            "spaceBelow": {"magnitude": 12, "unit": "PT"},
                        },
                    },
                },
                {
                    "startIndex": 46,
                    "endIndex": 297,
                    "paragraph": {
                        "elements": [
                            {
                                "startIndex": 46,
                                "endIndex": 146,
                                "textRun": {
                                    "content": (
                                        "LLMs acting on behalf of humans and interacting with real-"
                                        "world systems isn't theoretical anymore - "
                                    ),
                                    "textStyle": {},
                                },
                            },
                            {
                                "startIndex": 146,
                                "endIndex": 175,
                                "textRun": {
                                    "content": "Arcade has made it a reality.",
                                    "textStyle": {
                                        "bold": True,
                                        "italic": True,
                                    },
                                },
                            },
                            {
                                "startIndex": 175,
                                "endIndex": 248,
                                "textRun": {
                                    "content": (
                                        " With this shift, we're seeing the emergence of a new "
                                        "software practice: "
                                    ),
                                    "textStyle": {},
                                },
                            },
                            {
                                "startIndex": 248,
                                "endIndex": 295,
                                "textRun": {
                                    "content": "Machine Experience Engineering (MX Engineering)",
                                    "textStyle": {
                                        "italic": True,
                                    },
                                },
                            },
                            {
                                "startIndex": 295,
                                "endIndex": 297,
                                "textRun": {
                                    "content": ".\n",
                                    "textStyle": {},
                                },
                            },
                        ],
                        "paragraphStyle": {
                            "direction": "LEFT_TO_RIGHT",
                            "namedStyleType": "NORMAL_TEXT",
                            "spaceAbove": {"magnitude": 12, "unit": "PT"},
                            "spaceBelow": {"magnitude": 12, "unit": "PT"},
                        },
                    },
                },
                {
                    "endIndex": 407,
                    "startIndex": 297,
                    "table": {
                        "columns": 3,
                        "rows": 3,
                        "tableRows": [
                            {
                                "endIndex": 338,
                                "startIndex": 297,
                                "tableCells": [
                                    {
                                        "content": [
                                            {
                                                "endIndex": 318,
                                                "paragraph": {
                                                    "elements": [
                                                        {
                                                            "endIndex": 318,
                                                            "startIndex": 309,
                                                            "textRun": {
                                                                "content": "Column 1\n",
                                                                "textStyle": {"bold": True},
                                                            },
                                                        }
                                                    ],
                                                    "paragraphStyle": {
                                                        "alignment": "START",
                                                        "avoidWidowAndOrphan": False,
                                                        "borderBetween": {
                                                            "color": {},
                                                            "dashStyle": "SOLID",
                                                            "padding": {"unit": "PT"},
                                                            "width": {"unit": "PT"},
                                                        },
                                                        "borderBottom": {
                                                            "color": {},
                                                            "dashStyle": "SOLID",
                                                            "padding": {"unit": "PT"},
                                                            "width": {"unit": "PT"},
                                                        },
                                                        "borderLeft": {
                                                            "color": {},
                                                            "dashStyle": "SOLID",
                                                            "padding": {"unit": "PT"},
                                                            "width": {"unit": "PT"},
                                                        },
                                                        "borderRight": {
                                                            "color": {},
                                                            "dashStyle": "SOLID",
                                                            "padding": {"unit": "PT"},
                                                            "width": {"unit": "PT"},
                                                        },
                                                        "borderTop": {
                                                            "color": {},
                                                            "dashStyle": "SOLID",
                                                            "padding": {"unit": "PT"},
                                                            "width": {"unit": "PT"},
                                                        },
                                                        "direction": "LEFT_TO_RIGHT",
                                                        "indentEnd": {"unit": "PT"},
                                                        "indentFirstLine": {"unit": "PT"},
                                                        "indentStart": {"unit": "PT"},
                                                        "keepLinesTogether": False,
                                                        "keepWithNext": False,
                                                        "lineSpacing": 100,
                                                        "namedStyleType": "NORMAL_TEXT",
                                                        "pageBreakBefore": False,
                                                        "shading": {"backgroundColor": {}},
                                                        "spaceAbove": {"unit": "PT"},
                                                        "spaceBelow": {"unit": "PT"},
                                                        "spacingMode": "COLLAPSE_LISTS",
                                                    },
                                                },
                                                "startIndex": 309,
                                            }
                                        ],
                                        "endIndex": 318,
                                        "startIndex": 308,
                                        "tableCellStyle": {
                                            "backgroundColor": {},
                                            "columnSpan": 1,
                                            "contentAlignment": "TOP",
                                            "paddingBottom": {"magnitude": 5, "unit": "PT"},
                                            "paddingLeft": {"magnitude": 5, "unit": "PT"},
                                            "paddingRight": {"magnitude": 5, "unit": "PT"},
                                            "paddingTop": {"magnitude": 5, "unit": "PT"},
                                            "rowSpan": 1,
                                        },
                                    },
                                    {
                                        "content": [
                                            {
                                                "endIndex": 334,
                                                "paragraph": {
                                                    "elements": [
                                                        {
                                                            "endIndex": 326,
                                                            "startIndex": 319,
                                                            "textRun": {
                                                                "content": "Another",
                                                                "textStyle": {"italic": True},
                                                            },
                                                        },
                                                        {
                                                            "endIndex": 334,
                                                            "startIndex": 326,
                                                            "textRun": {
                                                                "content": " column\n",
                                                                "textStyle": {},
                                                            },
                                                        },
                                                    ],
                                                    "paragraphStyle": {
                                                        "alignment": "START",
                                                        "avoidWidowAndOrphan": False,
                                                        "borderBetween": {
                                                            "color": {},
                                                            "dashStyle": "SOLID",
                                                            "padding": {"unit": "PT"},
                                                            "width": {"unit": "PT"},
                                                        },
                                                        "borderBottom": {
                                                            "color": {},
                                                            "dashStyle": "SOLID",
                                                            "padding": {"unit": "PT"},
                                                            "width": {"unit": "PT"},
                                                        },
                                                        "borderLeft": {
                                                            "color": {},
                                                            "dashStyle": "SOLID",
                                                            "padding": {"unit": "PT"},
                                                            "width": {"unit": "PT"},
                                                        },
                                                        "borderRight": {
                                                            "color": {},
                                                            "dashStyle": "SOLID",
                                                            "padding": {"unit": "PT"},
                                                            "width": {"unit": "PT"},
                                                        },
                                                        "borderTop": {
                                                            "color": {},
                                                            "dashStyle": "SOLID",
                                                            "padding": {"unit": "PT"},
                                                            "width": {"unit": "PT"},
                                                        },
                                                        "direction": "LEFT_TO_RIGHT",
                                                        "indentEnd": {"unit": "PT"},
                                                        "indentFirstLine": {"unit": "PT"},
                                                        "indentStart": {"unit": "PT"},
                                                        "keepLinesTogether": False,
                                                        "keepWithNext": False,
                                                        "lineSpacing": 100,
                                                        "namedStyleType": "NORMAL_TEXT",
                                                        "pageBreakBefore": False,
                                                        "shading": {"backgroundColor": {}},
                                                        "spaceAbove": {"unit": "PT"},
                                                        "spaceBelow": {"unit": "PT"},
                                                        "spacingMode": "COLLAPSE_LISTS",
                                                    },
                                                },
                                                "startIndex": 319,
                                            }
                                        ],
                                        "endIndex": 334,
                                        "startIndex": 318,
                                        "tableCellStyle": {
                                            "backgroundColor": {},
                                            "columnSpan": 1,
                                            "contentAlignment": "TOP",
                                            "paddingBottom": {"magnitude": 5, "unit": "PT"},
                                            "paddingLeft": {"magnitude": 5, "unit": "PT"},
                                            "paddingRight": {"magnitude": 5, "unit": "PT"},
                                            "paddingTop": {"magnitude": 5, "unit": "PT"},
                                            "rowSpan": 1,
                                        },
                                    },
                                    {
                                        "content": [
                                            {
                                                "endIndex": 348,
                                                "paragraph": {
                                                    "elements": [
                                                        {
                                                            "endIndex": 348,
                                                            "startIndex": 335,
                                                            "textRun": {
                                                                "content": "Third column\n",
                                                                "textStyle": {},
                                                            },
                                                        }
                                                    ],
                                                    "paragraphStyle": {
                                                        "alignment": "START",
                                                        "avoidWidowAndOrphan": False,
                                                        "borderBetween": {
                                                            "color": {},
                                                            "dashStyle": "SOLID",
                                                            "padding": {"unit": "PT"},
                                                            "width": {"unit": "PT"},
                                                        },
                                                        "borderBottom": {
                                                            "color": {},
                                                            "dashStyle": "SOLID",
                                                            "padding": {"unit": "PT"},
                                                            "width": {"unit": "PT"},
                                                        },
                                                        "borderLeft": {
                                                            "color": {},
                                                            "dashStyle": "SOLID",
                                                            "padding": {"unit": "PT"},
                                                            "width": {"unit": "PT"},
                                                        },
                                                        "borderRight": {
                                                            "color": {},
                                                            "dashStyle": "SOLID",
                                                            "padding": {"unit": "PT"},
                                                            "width": {"unit": "PT"},
                                                        },
                                                        "borderTop": {
                                                            "color": {},
                                                            "dashStyle": "SOLID",
                                                            "padding": {"unit": "PT"},
                                                            "width": {"unit": "PT"},
                                                        },
                                                        "direction": "LEFT_TO_RIGHT",
                                                        "indentEnd": {"unit": "PT"},
                                                        "indentFirstLine": {"unit": "PT"},
                                                        "indentStart": {"unit": "PT"},
                                                        "keepLinesTogether": False,
                                                        "keepWithNext": False,
                                                        "lineSpacing": 100,
                                                        "namedStyleType": "NORMAL_TEXT",
                                                        "pageBreakBefore": False,
                                                        "shading": {"backgroundColor": {}},
                                                        "spaceAbove": {"unit": "PT"},
                                                        "spaceBelow": {"unit": "PT"},
                                                        "spacingMode": "COLLAPSE_LISTS",
                                                    },
                                                },
                                                "startIndex": 335,
                                            }
                                        ],
                                        "endIndex": 348,
                                        "startIndex": 334,
                                        "tableCellStyle": {
                                            "backgroundColor": {},
                                            "columnSpan": 1,
                                            "contentAlignment": "TOP",
                                            "paddingBottom": {"magnitude": 5, "unit": "PT"},
                                            "paddingLeft": {"magnitude": 5, "unit": "PT"},
                                            "paddingRight": {"magnitude": 5, "unit": "PT"},
                                            "paddingTop": {"magnitude": 5, "unit": "PT"},
                                            "rowSpan": 1,
                                        },
                                    },
                                ],
                                "tableRowStyle": {"minRowHeight": {"unit": "PT"}},
                            },
                            {
                                "endIndex": 366,
                                "startIndex": 348,
                                "tableCells": [
                                    {
                                        "content": [
                                            {
                                                "endIndex": 356,
                                                "paragraph": {
                                                    "elements": [
                                                        {
                                                            "endIndex": 356,
                                                            "startIndex": 350,
                                                            "textRun": {
                                                                "content": "Hello\n",
                                                                "textStyle": {},
                                                            },
                                                        }
                                                    ],
                                                    "paragraphStyle": {
                                                        "alignment": "START",
                                                        "avoidWidowAndOrphan": False,
                                                        "borderBetween": {
                                                            "color": {},
                                                            "dashStyle": "SOLID",
                                                            "padding": {"unit": "PT"},
                                                            "width": {"unit": "PT"},
                                                        },
                                                        "borderBottom": {
                                                            "color": {},
                                                            "dashStyle": "SOLID",
                                                            "padding": {"unit": "PT"},
                                                            "width": {"unit": "PT"},
                                                        },
                                                        "borderLeft": {
                                                            "color": {},
                                                            "dashStyle": "SOLID",
                                                            "padding": {"unit": "PT"},
                                                            "width": {"unit": "PT"},
                                                        },
                                                        "borderRight": {
                                                            "color": {},
                                                            "dashStyle": "SOLID",
                                                            "padding": {"unit": "PT"},
                                                            "width": {"unit": "PT"},
                                                        },
                                                        "borderTop": {
                                                            "color": {},
                                                            "dashStyle": "SOLID",
                                                            "padding": {"unit": "PT"},
                                                            "width": {"unit": "PT"},
                                                        },
                                                        "direction": "LEFT_TO_RIGHT",
                                                        "indentEnd": {"unit": "PT"},
                                                        "indentFirstLine": {"unit": "PT"},
                                                        "indentStart": {"unit": "PT"},
                                                        "keepLinesTogether": False,
                                                        "keepWithNext": False,
                                                        "lineSpacing": 100,
                                                        "namedStyleType": "NORMAL_TEXT",
                                                        "pageBreakBefore": False,
                                                        "shading": {"backgroundColor": {}},
                                                        "spaceAbove": {"unit": "PT"},
                                                        "spaceBelow": {"unit": "PT"},
                                                        "spacingMode": "COLLAPSE_LISTS",
                                                    },
                                                },
                                                "startIndex": 350,
                                            }
                                        ],
                                        "endIndex": 356,
                                        "startIndex": 349,
                                        "tableCellStyle": {
                                            "backgroundColor": {},
                                            "columnSpan": 1,
                                            "contentAlignment": "TOP",
                                            "paddingBottom": {"magnitude": 5, "unit": "PT"},
                                            "paddingLeft": {"magnitude": 5, "unit": "PT"},
                                            "paddingRight": {"magnitude": 5, "unit": "PT"},
                                            "paddingTop": {"magnitude": 5, "unit": "PT"},
                                            "rowSpan": 1,
                                        },
                                    },
                                    {
                                        "content": [
                                            {
                                                "endIndex": 364,
                                                "paragraph": {
                                                    "elements": [
                                                        {
                                                            "endIndex": 364,
                                                            "startIndex": 357,
                                                            "textRun": {
                                                                "content": "world!\n",
                                                                "textStyle": {},
                                                            },
                                                        }
                                                    ],
                                                    "paragraphStyle": {
                                                        "alignment": "START",
                                                        "avoidWidowAndOrphan": False,
                                                        "borderBetween": {
                                                            "color": {},
                                                            "dashStyle": "SOLID",
                                                            "padding": {"unit": "PT"},
                                                            "width": {"unit": "PT"},
                                                        },
                                                        "borderBottom": {
                                                            "color": {},
                                                            "dashStyle": "SOLID",
                                                            "padding": {"unit": "PT"},
                                                            "width": {"unit": "PT"},
                                                        },
                                                        "borderLeft": {
                                                            "color": {},
                                                            "dashStyle": "SOLID",
                                                            "padding": {"unit": "PT"},
                                                            "width": {"unit": "PT"},
                                                        },
                                                        "borderRight": {
                                                            "color": {},
                                                            "dashStyle": "SOLID",
                                                            "padding": {"unit": "PT"},
                                                            "width": {"unit": "PT"},
                                                        },
                                                        "borderTop": {
                                                            "color": {},
                                                            "dashStyle": "SOLID",
                                                            "padding": {"unit": "PT"},
                                                            "width": {"unit": "PT"},
                                                        },
                                                        "direction": "LEFT_TO_RIGHT",
                                                        "indentEnd": {"unit": "PT"},
                                                        "indentFirstLine": {"unit": "PT"},
                                                        "indentStart": {"unit": "PT"},
                                                        "keepLinesTogether": False,
                                                        "keepWithNext": False,
                                                        "lineSpacing": 100,
                                                        "namedStyleType": "NORMAL_TEXT",
                                                        "pageBreakBefore": False,
                                                        "shading": {"backgroundColor": {}},
                                                        "spaceAbove": {"unit": "PT"},
                                                        "spaceBelow": {"unit": "PT"},
                                                        "spacingMode": "COLLAPSE_LISTS",
                                                    },
                                                },
                                                "startIndex": 357,
                                            }
                                        ],
                                        "endIndex": 364,
                                        "startIndex": 356,
                                        "tableCellStyle": {
                                            "backgroundColor": {},
                                            "columnSpan": 1,
                                            "contentAlignment": "TOP",
                                            "paddingBottom": {"magnitude": 5, "unit": "PT"},
                                            "paddingLeft": {"magnitude": 5, "unit": "PT"},
                                            "paddingRight": {"magnitude": 5, "unit": "PT"},
                                            "paddingTop": {"magnitude": 5, "unit": "PT"},
                                            "rowSpan": 1,
                                        },
                                    },
                                    {
                                        "content": [
                                            {
                                                "endIndex": 366,
                                                "paragraph": {
                                                    "elements": [
                                                        {
                                                            "endIndex": 366,
                                                            "startIndex": 365,
                                                            "textRun": {
                                                                "content": "\n",
                                                                "textStyle": {},
                                                            },
                                                        }
                                                    ],
                                                    "paragraphStyle": {
                                                        "alignment": "START",
                                                        "avoidWidowAndOrphan": False,
                                                        "borderBetween": {
                                                            "color": {},
                                                            "dashStyle": "SOLID",
                                                            "padding": {"unit": "PT"},
                                                            "width": {"unit": "PT"},
                                                        },
                                                        "borderBottom": {
                                                            "color": {},
                                                            "dashStyle": "SOLID",
                                                            "padding": {"unit": "PT"},
                                                            "width": {"unit": "PT"},
                                                        },
                                                        "borderLeft": {
                                                            "color": {},
                                                            "dashStyle": "SOLID",
                                                            "padding": {"unit": "PT"},
                                                            "width": {"unit": "PT"},
                                                        },
                                                        "borderRight": {
                                                            "color": {},
                                                            "dashStyle": "SOLID",
                                                            "padding": {"unit": "PT"},
                                                            "width": {"unit": "PT"},
                                                        },
                                                        "borderTop": {
                                                            "color": {},
                                                            "dashStyle": "SOLID",
                                                            "padding": {"unit": "PT"},
                                                            "width": {"unit": "PT"},
                                                        },
                                                        "direction": "LEFT_TO_RIGHT",
                                                        "indentEnd": {"unit": "PT"},
                                                        "indentFirstLine": {"unit": "PT"},
                                                        "indentStart": {"unit": "PT"},
                                                        "keepLinesTogether": False,
                                                        "keepWithNext": False,
                                                        "lineSpacing": 100,
                                                        "namedStyleType": "NORMAL_TEXT",
                                                        "pageBreakBefore": False,
                                                        "shading": {"backgroundColor": {}},
                                                        "spaceAbove": {"unit": "PT"},
                                                        "spaceBelow": {"unit": "PT"},
                                                        "spacingMode": "COLLAPSE_LISTS",
                                                    },
                                                },
                                                "startIndex": 365,
                                            }
                                        ],
                                        "endIndex": 366,
                                        "startIndex": 364,
                                        "tableCellStyle": {
                                            "backgroundColor": {},
                                            "columnSpan": 1,
                                            "contentAlignment": "TOP",
                                            "paddingBottom": {"magnitude": 5, "unit": "PT"},
                                            "paddingLeft": {"magnitude": 5, "unit": "PT"},
                                            "paddingRight": {"magnitude": 5, "unit": "PT"},
                                            "paddingTop": {"magnitude": 5, "unit": "PT"},
                                            "rowSpan": 1,
                                        },
                                    },
                                ],
                                "tableRowStyle": {"minRowHeight": {"unit": "PT"}},
                            },
                            {
                                "endIndex": 415,
                                "startIndex": 366,
                                "tableCells": [
                                    {
                                        "content": [
                                            {
                                                "endIndex": 388,
                                                "paragraph": {
                                                    "elements": [
                                                        {
                                                            "endIndex": 388,
                                                            "startIndex": 368,
                                                            "textRun": {
                                                                "content": "The quick brown fox\n",
                                                                "textStyle": {},
                                                            },
                                                        }
                                                    ],
                                                    "paragraphStyle": {
                                                        "alignment": "START",
                                                        "avoidWidowAndOrphan": False,
                                                        "borderBetween": {
                                                            "color": {},
                                                            "dashStyle": "SOLID",
                                                            "padding": {"unit": "PT"},
                                                            "width": {"unit": "PT"},
                                                        },
                                                        "borderBottom": {
                                                            "color": {},
                                                            "dashStyle": "SOLID",
                                                            "padding": {"unit": "PT"},
                                                            "width": {"unit": "PT"},
                                                        },
                                                        "borderLeft": {
                                                            "color": {},
                                                            "dashStyle": "SOLID",
                                                            "padding": {"unit": "PT"},
                                                            "width": {"unit": "PT"},
                                                        },
                                                        "borderRight": {
                                                            "color": {},
                                                            "dashStyle": "SOLID",
                                                            "padding": {"unit": "PT"},
                                                            "width": {"unit": "PT"},
                                                        },
                                                        "borderTop": {
                                                            "color": {},
                                                            "dashStyle": "SOLID",
                                                            "padding": {"unit": "PT"},
                                                            "width": {"unit": "PT"},
                                                        },
                                                        "direction": "LEFT_TO_RIGHT",
                                                        "indentEnd": {"unit": "PT"},
                                                        "indentFirstLine": {"unit": "PT"},
                                                        "indentStart": {"unit": "PT"},
                                                        "keepLinesTogether": False,
                                                        "keepWithNext": False,
                                                        "lineSpacing": 100,
                                                        "namedStyleType": "NORMAL_TEXT",
                                                        "pageBreakBefore": False,
                                                        "shading": {"backgroundColor": {}},
                                                        "spaceAbove": {"unit": "PT"},
                                                        "spaceBelow": {"unit": "PT"},
                                                        "spacingMode": "COLLAPSE_LISTS",
                                                    },
                                                },
                                                "startIndex": 368,
                                            }
                                        ],
                                        "endIndex": 388,
                                        "startIndex": 367,
                                        "tableCellStyle": {
                                            "backgroundColor": {},
                                            "columnSpan": 1,
                                            "contentAlignment": "TOP",
                                            "paddingBottom": {"magnitude": 5, "unit": "PT"},
                                            "paddingLeft": {"magnitude": 5, "unit": "PT"},
                                            "paddingRight": {"magnitude": 5, "unit": "PT"},
                                            "paddingTop": {"magnitude": 5, "unit": "PT"},
                                            "rowSpan": 1,
                                        },
                                    },
                                    {
                                        "content": [
                                            {
                                                "endIndex": 401,
                                                "paragraph": {
                                                    "elements": [
                                                        {
                                                            "endIndex": 395,
                                                            "startIndex": 389,
                                                            "textRun": {
                                                                "content": "jumped",
                                                                "textStyle": {"italic": True},
                                                            },
                                                        },
                                                        {
                                                            "endIndex": 401,
                                                            "startIndex": 395,
                                                            "textRun": {
                                                                "content": " over\n",
                                                                "textStyle": {},
                                                            },
                                                        },
                                                    ],
                                                    "paragraphStyle": {
                                                        "alignment": "START",
                                                        "avoidWidowAndOrphan": False,
                                                        "borderBetween": {
                                                            "color": {},
                                                            "dashStyle": "SOLID",
                                                            "padding": {"unit": "PT"},
                                                            "width": {"unit": "PT"},
                                                        },
                                                        "borderBottom": {
                                                            "color": {},
                                                            "dashStyle": "SOLID",
                                                            "padding": {"unit": "PT"},
                                                            "width": {"unit": "PT"},
                                                        },
                                                        "borderLeft": {
                                                            "color": {},
                                                            "dashStyle": "SOLID",
                                                            "padding": {"unit": "PT"},
                                                            "width": {"unit": "PT"},
                                                        },
                                                        "borderRight": {
                                                            "color": {},
                                                            "dashStyle": "SOLID",
                                                            "padding": {"unit": "PT"},
                                                            "width": {"unit": "PT"},
                                                        },
                                                        "borderTop": {
                                                            "color": {},
                                                            "dashStyle": "SOLID",
                                                            "padding": {"unit": "PT"},
                                                            "width": {"unit": "PT"},
                                                        },
                                                        "direction": "LEFT_TO_RIGHT",
                                                        "indentEnd": {"unit": "PT"},
                                                        "indentFirstLine": {"unit": "PT"},
                                                        "indentStart": {"unit": "PT"},
                                                        "keepLinesTogether": False,
                                                        "keepWithNext": False,
                                                        "lineSpacing": 100,
                                                        "namedStyleType": "NORMAL_TEXT",
                                                        "pageBreakBefore": False,
                                                        "shading": {"backgroundColor": {}},
                                                        "spaceAbove": {"unit": "PT"},
                                                        "spaceBelow": {"unit": "PT"},
                                                        "spacingMode": "COLLAPSE_LISTS",
                                                    },
                                                },
                                                "startIndex": 389,
                                            }
                                        ],
                                        "endIndex": 401,
                                        "startIndex": 388,
                                        "tableCellStyle": {
                                            "backgroundColor": {},
                                            "columnSpan": 1,
                                            "contentAlignment": "TOP",
                                            "paddingBottom": {"magnitude": 5, "unit": "PT"},
                                            "paddingLeft": {"magnitude": 5, "unit": "PT"},
                                            "paddingRight": {"magnitude": 5, "unit": "PT"},
                                            "paddingTop": {"magnitude": 5, "unit": "PT"},
                                            "rowSpan": 1,
                                        },
                                    },
                                    {
                                        "content": [
                                            {
                                                "endIndex": 415,
                                                "paragraph": {
                                                    "elements": [
                                                        {
                                                            "endIndex": 415,
                                                            "startIndex": 402,
                                                            "textRun": {
                                                                "content": "the lazy dog\n",
                                                                "textStyle": {},
                                                            },
                                                        }
                                                    ],
                                                    "paragraphStyle": {
                                                        "alignment": "START",
                                                        "avoidWidowAndOrphan": False,
                                                        "borderBetween": {
                                                            "color": {},
                                                            "dashStyle": "SOLID",
                                                            "padding": {"unit": "PT"},
                                                            "width": {"unit": "PT"},
                                                        },
                                                        "borderBottom": {
                                                            "color": {},
                                                            "dashStyle": "SOLID",
                                                            "padding": {"unit": "PT"},
                                                            "width": {"unit": "PT"},
                                                        },
                                                        "borderLeft": {
                                                            "color": {},
                                                            "dashStyle": "SOLID",
                                                            "padding": {"unit": "PT"},
                                                            "width": {"unit": "PT"},
                                                        },
                                                        "borderRight": {
                                                            "color": {},
                                                            "dashStyle": "SOLID",
                                                            "padding": {"unit": "PT"},
                                                            "width": {"unit": "PT"},
                                                        },
                                                        "borderTop": {
                                                            "color": {},
                                                            "dashStyle": "SOLID",
                                                            "padding": {"unit": "PT"},
                                                            "width": {"unit": "PT"},
                                                        },
                                                        "direction": "LEFT_TO_RIGHT",
                                                        "indentEnd": {"unit": "PT"},
                                                        "indentFirstLine": {"unit": "PT"},
                                                        "indentStart": {"unit": "PT"},
                                                        "keepLinesTogether": False,
                                                        "keepWithNext": False,
                                                        "lineSpacing": 100,
                                                        "namedStyleType": "NORMAL_TEXT",
                                                        "pageBreakBefore": False,
                                                        "shading": {"backgroundColor": {}},
                                                        "spaceAbove": {"unit": "PT"},
                                                        "spaceBelow": {"unit": "PT"},
                                                        "spacingMode": "COLLAPSE_LISTS",
                                                    },
                                                },
                                                "startIndex": 402,
                                            }
                                        ],
                                        "endIndex": 415,
                                        "startIndex": 401,
                                        "tableCellStyle": {
                                            "backgroundColor": {},
                                            "columnSpan": 1,
                                            "contentAlignment": "TOP",
                                            "paddingBottom": {"magnitude": 5, "unit": "PT"},
                                            "paddingLeft": {"magnitude": 5, "unit": "PT"},
                                            "paddingRight": {"magnitude": 5, "unit": "PT"},
                                            "paddingTop": {"magnitude": 5, "unit": "PT"},
                                            "rowSpan": 1,
                                        },
                                    },
                                ],
                                "tableRowStyle": {"minRowHeight": {"unit": "PT"}},
                            },
                        ],
                        "tableStyle": {
                            "tableColumnProperties": [
                                {"widthType": "EVENLY_DISTRIBUTED"},
                                {"widthType": "EVENLY_DISTRIBUTED"},
                                {"widthType": "EVENLY_DISTRIBUTED"},
                            ]
                        },
                    },
                },
            ]
        },
    }

    expected_markdown = (
        "---\ntitle: The Birth of Machine Experience Engineering\ndocumentId: 1234567890\n---\n"
        "# **The Birth of Machine Experience Engineering**\n"
        "\n"
        "LLMs acting on behalf of humans and interacting with real-world systems isn't theoretical "
        "anymore - "
        "**_Arcade has made it a reality._** With this shift, we're seeing the emergence of a new "
        "software practice: "
        "_Machine Experience Engineering (MX Engineering)_.\n"
        "<table>"
        "<tr>"
        "<td><b>Column 1</b></td>"
        "<td><i>Another</i> column</td>"
        "<td>Third column</td>"
        "</tr>"
        "<tr>"
        "<td>Hello</td>"
        "<td>world!</td>"
        "<td></td>"
        "</tr>"
        "<tr>"
        "<td>The quick brown fox</td>"
        "<td><i>jumped</i> over</td>"
        "<td>the lazy dog</td>"
        "</tr>"
        "</table>"
    )

    expected_html = (
        "<html><head>"
        "<title>The Birth of Machine Experience Engineering</title>"
        '<meta name="documentId" content="1234567890">'
        "</head><body>"
        "<h1><b>The Birth of Machine Experience Engineering</b></h1>"
        "<p>LLMs acting on behalf of humans and interacting with real-world systems isn't "
        "theoretical anymore - "
        "<b><i>Arcade has made it a reality.</i></b> With this shift, we're seeing the emergence "
        "of a new software practice: <i>Machine Experience Engineering (MX Engineering)</i>.</p>"
        "<table>"
        "<tr>"
        "<td><b>Column 1</b></td>"
        "<td><i>Another</i> column</td>"
        "<td>Third column</td>"
        "</tr>"
        "<tr>"
        "<td>Hello</td>"
        "<td>world!</td>"
        "<td></td>"
        "</tr>"
        "<tr>"
        "<td>The quick brown fox</td>"
        "<td><i>jumped</i> over</td>"
        "<td>the lazy dog</td>"
        "</tr>"
        "</table>"
        "</body></html>"
    )

    return document, expected_markdown, expected_html
