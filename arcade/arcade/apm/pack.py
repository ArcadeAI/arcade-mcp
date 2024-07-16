import os
from pathlib import Path
from typing import Union

import toml
from pydantic import ValidationError

from arcade.apm.base import PackInfo, ToolPack
from arcade.apm.parse import get_tools_from_file
from arcade.utils import snake_to_pascal_case


class Packer:
    def __init__(self, pack_dir: Union[str, os.PathLike]):
        self.pack_dir = Path(pack_dir).resolve()
        self.tools_dir = self.pack_dir / "tools"
        # Load the action pack configuration from a TOML file
        try:
            with open(self.pack_dir / "pack.toml") as f:
                pack_data = toml.load(f)

            self.pack = PackInfo(**pack_data["pack"])
            self.modules = pack_data["modules"]

        except FileNotFoundError:
            raise FileNotFoundError(f"No 'pack.toml' found in {self.tools_dir}")
        except (toml.TomlDecodeError, ValidationError) as e:
            raise ValueError(f"Invalid 'pack.toml' format: {e}")

        self.tools = self.load_tools()
        self.depends: dict[str, str] = {}  # TODO
        # self.packs = []  # TODO

    def load_tools(self) -> dict[str, str]:
        """
        Find and load the from the tools defined within directory
        """
        tools = {}
        for tool_file in self.tools_dir.rglob("*.py"):
            if "__init__.py" in tool_file.name:
                continue
            try:
                module = tool_file.stem
                version = self.modules.get(module, "latest")

                found_tools = get_tools_from_file(tool_file)
                for tool in found_tools:
                    tool_name = module + "." + tool + "@" + version
                    tools[snake_to_pascal_case(tool)] = tool_name
            except Exception as e:
                print(f"Error loading tool from {tool_file}: {e}")
        return tools

    def create_pack(self) -> None:
        """
        Create a tool pack
        """
        if not self.tools:
            raise ValueError("No tools found in the tools directory")
        pack = ToolPack(pack=self.pack, depends=self.depends, tools=self.tools)
        pack.write_lock_file(self.pack_dir)
