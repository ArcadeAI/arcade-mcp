TOOLKIT_PAGE = """{header}

{table_of_contents}

{tools_specs}
{reference_mdx}
{footer}
"""

TOOLKIT_HEADER = """# {toolkit_title}

import ToolInfo from "@/components/ToolInfo";
import Badges from "@/components/Badges";
import TabbedCodeBlock from "@/components/TabbedCodeBlock";
import TableOfContents from "@/components/TableOfContents";
import ToolFooter from "@/components/ToolFooter";

<ToolInfo
  description="Enable agents to interact with {toolkit_title}"
  author="Arcade"
  {auth_type}
  versions={{["{version}"]}}
/>

<Badges repo="arcadeai/{pip_package_name}" />

{description}"""

TABLE_OF_CONTENTS = """## Available Tools

<TableOfContents
  headers={{["Tool Name", "Description"]}}
  data={{
    [{tool_items}
    ]
  }}
/>

<Tip>
  If you need to perform an action that's not listed here, you can [get in touch
  with us](mailto:contact@arcade.dev) to request a new tool, or [create your
  own tools](/home/build-tools/create-a-toolkit).
</Tip>"""

TABLE_OF_CONTENTS_ITEM = '\n      ["{tool_fully_qualified_name}", "{description}"],'

TOOL_SPEC = """## {tool_fully_qualified_name}

<br />
{tabbed_examples_list}

{description}

**Parameters**

{parameters}
{secrets}
"""

TOOL_SPEC_SECRETS = """**Secrets**

This tool requires the following secrets: {secrets} (learn how to [configure secrets](/home/build-tools/create-a-tool-with-secrets#supplying-the-secret))
"""

TABBED_EXAMPLES_LIST = """<TabbedCodeBlock
  tabs={{[
    {{
      label: "Call the Tool Directly",
      content: {{
        Python: ["/examples/integrations/toolkits/{toolkit_name}/{tool_name}_example_call_tool.py"],
        JavaScript: ["/examples/integrations/toolkits/{toolkit_name}/{tool_name}_example_call_tool.js"],
      }},
    }},
  ]}}
/>"""

TOOL_PARAMETER = "- **{param_name}** ({definition}) {description}"

TOOLKIT_FOOTER = """<ToolFooter pipPackageName="{pip_package_name}" />"""

TOOLKIT_FOOTER_OAUTH2 = """## Auth

{provider_configuration}

<ToolFooter pipPackageName="{pip_package_name}" />
"""

WELL_KNOWN_PROVIDER_CONFIG = "The Arcade {toolkit_name} toolkit uses the [{provider_name} auth provider](/home/auth-providers/{provider_id}) to connect to users' {toolkit_name} accounts. Please refer to the [{provider_name} auth provider](/home/auth-providers/{provider_id}) documentation to learn how to configure auth."

GENERIC_PROVIDER_CONFIG = "The {toolkit_name} toolkit uses the Auth Provider with id `{provider_id}` to connect to users' {toolkit_name} accounts. In order to use the toolkit, you will need to configure the `{provider_id}` auth provider."

TOOL_CALL_EXAMPLE_JS = """import {{ Arcade }} from "@arcadeai/arcadejs";

const client = new Arcade(); // Automatically finds the `ARCADE_API_KEY` env variable

const USER_ID = "{{arcade_user_id}}";
const TOOL_NAME = "{tool_fully_qualified_name}";

// Start the authorization process
const authResponse = await client.tools.authorize({{
    tool_name: TOOL_NAME,
    user_id: USER_ID
}});

if (authResponse.status !== "completed") {{
  console.log(`Click this link to authorize: ${{authResponse.url}}`);
}}

// Wait for the authorization to complete
await client.auth.waitForCompletion(authResponse);

const toolInput = {input_map};

const response = await client.tools.execute({{
  tool_name: TOOL_NAME,
  input: toolInput,
  user_id: USER_ID,
}});

console.log(JSON.stringify(response.output.value, null, 2));
"""

TOOL_CALL_EXAMPLE_PY = """import json
from arcadepy import Arcade

client = Arcade()  # Automatically finds the `ARCADE_API_KEY` env variable

USER_ID = "{{arcade_user_id}}"
TOOL_NAME = "{tool_fully_qualified_name}"

auth_response = client.tools.authorize(
    tool_name=TOOL_NAME,
    user_id=TOOL_NAME
)

if auth_response.status != "completed":
    print(f"Click this link to authorize: {{auth_response.url}}")

# Wait for the authorization to complete
client.auth.wait_for_completion(auth_response)

tool_input = {input_map}

response = client.tools.execute(
    tool_name=TOOL_NAME,
    input=tool_input,
    user_id=USER_ID,
)
print(json.dumps(response.output.value, indent=2))
"""

ENUM_MDX = """## Reference

Below is a reference of enumerations used by some of the tools in the {toolkit_name} toolkit:

{enum_items}
"""

ENUM_ITEM = """## {enum_name}

{enum_values}
"""

ENUM_VALUE = "- **{enum_option_name}**: `{enum_option_value}`"
