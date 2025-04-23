update_draft_email_additional_messages = [
    {"role": "system", "content": "Today is 2025-04-22, Tuesday."},
    {
        "role": "user",
        "content": '"create a new draft email with subject \'Hello friends\' and body "\n"\'I\'ve gathered you all here to celebrate the launch of the new Arcade platform."\n            "address it to e@arcade.dev and z@arcade.dev. also carbon copy to j@arcade.dev, "\n"f@arcade.dev, k@arcade.dev and finally to m@arcade.dev. also bcc to r@arcade.dev"',  # noqa: E501
    },
    {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": "call_lKw4S01FGe03oZeuW25roepy",
                "type": "function",
                "function": {
                    "name": "Microsoft_CreateDraftEmail",
                    "arguments": '{"subject":"Hello friends","body":"I\'ve gathered you all here to celebrate the launch of the new Arcade platform.","to_recipients":["e@arcade.dev","z@arcade.dev"],"cc_recipients":["j@arcade.dev","f@arcade.dev","k@arcade.dev","m@arcade.dev"],"bcc_recipients":["r@arcade.dev"]}',  # noqa: E501
                },
            }
        ],
    },
    {
        "role": "tool",
        "content": '{"bcc_recipients":[{"email_address":"r@arcade.dev","name":"r@arcade.dev"}],"body":"I\'ve gathered you all here to celebrate the launch of the new Arcade platform.","cc_recipients":[{"email_address":"j@arcade.dev","name":"j@arcade.dev"},{"email_address":"f@arcade.dev","name":"f@arcade.dev"},{"email_address":"k@arcade.dev","name":"k@arcade.dev"},{"email_address":"m@arcade.dev","name":"m@arcade.dev"}],"conversation_id":"AQQkADAwATM0MDAAMi04Y2Y1LTQ3MTEALTAwAi0wMAoAEAAskq2oM-moTbt3gDT_yK0e","conversation_index":"AQHbs6c0LJKtqDP5qE27d4A0/sitHg==","flag":{"due_date_time":"","flag_status":"notFlagged"},"from":{"email_address":"","name":""},"has_attachments":false,"importance":"normal","is_draft":true,"is_read":true,"message_id":"AQMkADAwATM0MDAAMi04Y2Y1LTQ3MTEALTAwAi0wMAoARgAAAyXxSd3UxTpCkDpGouEg0JMHAFuxokOLZRtDncM4_x_WeUwAAAIBDwAAAFuxokOLZRtDncM4_x_WeUwAAAAC-dpvAAAA","received_date_time":"2025-04-22T16:54:25+00:00","reply_to":[],"subject":"Hello friends","to_recipients":[{"email_address":"e@arcade.dev","name":"e@arcade.dev"},{"email_address":"z@arcade.dev","name":"z@arcade.dev"}],"web_link":"https://outlook.live.com/owa/?ItemID=AQMkADAwATM0MDAAMi04Y2Y1LTQ3MTEALTAwAi0wMAoARgAAAyXxSd3UxTpCkDpGouEg0JMHAFuxokOLZRtDncM4%2Bx%2BWeUwAAAIBDwAAAFuxokOLZRtDncM4%2Bx%2BWeUwAAAAC%2FdpvAAAA\\u0026exvsurl=1\\u0026viewmodel=ReadMessageItem"}',  # noqa: E501
        "tool_call_id": "call_lKw4S01FGe03oZeuW25roepy",
        "name": "Microsoft_CreateDraftEmail",
    },
    {
        "role": "assistant",
        "content": 'I have created a draft email with the subject "Hello friends" addressed to the specified recipients. You can view and edit the draft through [this link](https://outlook.live.com/owa/?ItemID=AQMkADAwATM0MDAAMi04Y2Y1LTQ3MTEALTAwAi0wMAoARgAAAyXxSd3UxTpCkDpGouEg0JMHAFuxokOLZRtDncM4%2Bx%2BWeUwAAAIBDwAAAFuxokOLZRtDncM4%2Bx%2BWeUwAAAAC%2FdpvAAAA&exvsurl=1&viewmodel=ReadMessageItem).',  # noqa: E501
    },
]

list_emails_with_pagination_token_additional_messages = [
    {"role": "system", "content": "Today is 2025-04-21, Monday."},
    {"role": "user", "content": "get one email"},
    {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": "call_jACvc3Gl1WHkqWgI8gdsIt0G",
                "type": "function",
                "function": {"name": "Microsoft_ListEmails", "arguments": '{"limit":1}'},
            }
        ],
    },
    {
        "role": "tool",
        "content": '{"messages":[{"bcc_recipients":[],"body":"Microsoft account New app(s) have access to your data Arcade","cc_recipients":["e@arcade.dev],"conversation_id":"AQQkADAwATM0MDAAMi04Y2Y1LTQ3MTEALTAwAi0wMAoAEABOD15A17tWSaVHkmjhko1R","conversation_index":"AQHbsuDd Tg9eQNe7VkmlR5Jo4ZKNUQ==","flag":{"due_date_time":"","flag_status":"notFlagged"},"from":{"email_address":"account-security@accountprotect ion.microsoft.com","name":"Microsoft account team"},"has_attachments":false,"importance":"normal","is_draft":false,"is_read":true,"message_id":"AQMkADAwATM0MDAAMi04Y2Y1LTQ3MTEALTAwAi0wMAoARgAAAyXxSd3UxTpCkDpGouEg0JMHAFuxokOLZRtDncM4_x_WeUwAAAIBDAAAAFuxokOLZRtDncM4_x_WeUwAAAABc_ezAAAA","received_date_time":"2025-04-21T17:14:39+00:00", "reply_to":[],"subject":"New app(s) connected to your Microsoft account","to_recipients":[{"email_address":"ericarcade@outlook.com","name":"ericarcade@outlook.com"}],"web_link":"https://outlook.live.com/owa/?ItemID=AQMkADAwATM0MDAAMi04Y2Y1LTQ3MTEALTAwAi0wMAoARgAAAyXxSd3UxTpCkDpGouEg0JMHAFuxokOLZRtDncM4%2Bx%2BWeUwAAAIBDAAAAFuxokOLZRtDncM4%2Bx%2BWeUwAAAABc%2BezAAAA\\u0026exvsurl=1\\u0026viewmodel=ReadMessageItem"}],"num_messages":1,"pagination_token":"https://graph.microsoft.com/v1.0/me/messages?%24count=true&%24orderby=receivedDateTime+DESC&%24select=bccRecipients%2cbody%2cccRecipients%2cconversationId%2cconversationIndex%2cflag%2cfrom%2chasAttachments%2cimportance%2cisDraft%2cisRead%2creceivedDateTime%2creplyTo%2csubject%2ctoRecipients%2cwebLink&%24top=1&%24skip=1"}',  # noqa: E501
        "tool_call_id": "call_jACvc3Gl1WHkqWgI8gdsIt0G",
        "name": "Microsoft_ListEmails",
    },
    {
        "role": "assistant",
        "content": "Here is the most recent email you received:\n\n- **From:** Microsoft account team (account-security@accountprotection.microsoft.com)\n- **To:** e@outlook.com\n- **Subject:** New app(s) connected to your Microsoft account\n- **Received Date:** April 21, 2025\n- **Body:**\n  ```\n  Microsoft account\n\n  New app(s) have access to your data Arcade connected to the Microsoft account *@outlook.com.```\n- **Link to email:** [Read in Outlook](https://outlook.live.com/owa/?ItemID=AQMkADAwATM0MDAAMi04Y2Y1LTQ3MTEALTAwAi0wMAoARgAAAyXxSd3UxTpCkDpGouEg0JMHAFuxokOLZRtDncM4%2Bx%2BWeUwAAAIBDAAAAFuxokOLZRtDncM4%2Bx%2BWeUwAAAABc%2BezAAAA&exvsurl=1&viewmodel=ReadMessageItem)",  # noqa: E501
    },
]

list_emails_with_pagination_token_additional_messages = [
    {"role": "system", "content": "Today is 2025-04-21, Monday."},
    {"role": "user", "content": "get one email"},
    {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": "call_jACvc3Gl1WHkqWgI8gdsIt0G",
                "type": "function",
                "function": {"name": "Microsoft_ListEmails", "arguments": '{"limit":1}'},
            }
        ],
    },
    {
        "role": "tool",
        "content": '{"messages":[{"bcc_recipients":[],"body":"Microsoft account New app(s) have access to your data Arcade","cc_recipients":[],"conversation_id":"AQQkADAwATM0MDAAMi04Y2Y1LTQ3MTEALTAwAi0wMAoAEABOD15A17tWSaVHkmjhko1R","conversation_index":"AQHbsuDdTg9eQNe7VkmlR5Jo4ZKNUQ==","flag":{"due_date_time":"","flag_status":"notFlagged"},"from":{"email_address":"account-security-noreply@accountprotection.microsoft.com","name":"Microsoft account team"},"has_attachments":false,"importance":"normal","is_draft":false,"is_read":true,"message_id":"AQMkADAwATM0MDAAMi04Y2Y1LTQ3MTEALTAwAi0wMAoARgAAAyXxSd3UxTpCkDpGouEg0JMHAFuxokOLZRtDncM4_x_WeUwAAAIBDAAAAFuxokOLZRtDncM4_x_WeUwAAAABc_ezAAAA","received_date_time":"2025-04-21T17:14:39+00:00", "reply_to":[],"subject":"New app(s) connected to your Microsoft account","to_recipients":[{"email_address":"ericarcade@outlook.com","name":"ericarcade@outlook.com"}],"web_link":"https://outlook.live.com/owa/?I temID=AQMkADAwATM0MDAAMi04Y2Y1LTQ3MTEALTAwAi0wMAoARgAAAyXxSd3UxTpCkDpGouEg0JMHAFuxokOLZRtDncM4%2Bx%2BWeUwAAAIBDAAAAFuxokOLZRtDncM4%2Bx%2BWeUwAAAA Bc%2BezAAAA\\u0026exvsurl=1\\u0026viewmodel=ReadMessageItem"}],"num_messages":1,"pagination_token":"https://graph.microsoft.com/v1.0/me/messages?%24count=true&%24orderby=receivedDateTime+DESC&%24select=bccRecipients%2cbody%2cccRecipients%2cconversationId%2cconversationIndex%2cflag%2cfrom%2chasAttachments%2cimportance%2cisDraft%2cisRead%2creceivedDateTime%2creplyTo%2csubject%2ctoRecipients%2cwebLink&%24top=1&%24skip=1"}',  # noqa: E501
        "tool_call_id": "call_jACvc3Gl1WHkqWgI8gdsIt0G",
        "name": "Microsoft_ListEmails",
    },
    {
        "role": "assistant",
        "content": "Here is the most recent email you received:\n\n- **From:** Microsoft account team (account-security-noreply@accountprotection.microsoft.com)\n- **To:** e@outlook.com\n- **Subject:** New app(s) connected to your Microsoft account\n- **Received Date:** April 21, 2025\n- **Body:**\n  ```\n  Microsoft account\n\n  New app(s) have access to your data Arcade connected to the Microsoft account *@outlook.com.```\n- **Link to email:** [Read in Outlook](https://outlook.live.com/owa/?ItemID=AQMkADAwATM0MDAAMi04Y2Y1LTQ3MTEALTAwAi0wMAoARgAAAyXxSd3UxTpCkDpGouEg0JMHAFuxokOLZRtDncM4%2Bx%2BWeUwAAAIBDAAAAFuxokOLZRtDncM4%2Bx%2BWeUwAAAABc%2BezAAAA&exvsurl=1&viewmodel=ReadMessageItem)",  # noqa: E501
    },
]
