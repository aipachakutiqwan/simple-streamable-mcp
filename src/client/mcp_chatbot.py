import os
import asyncio
from contextlib import AsyncExitStack

import nest_asyncio
import mcp.types as types
from anthropic import Anthropic
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession, StdioServerParameters

from src.log_management.config import get_app_config_parameters


class McpChatBot:
    def __init__(self, run_locally, connectors_config):
        """
        Initialize the McpChatBot instance.
        Args:
            :param run_locally: Boolean indicating whether to run locally.
            :param connectors_config: Configuration for connectors from
                                      local or server file configuration
        """
        self.run_locally = run_locally
        self.connectors_config = connectors_config
        self.exit_stack = AsyncExitStack()
        self.anthropic = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.available_tools = []
        self.available_prompts = []
        self.sessions = {}
        self.url_mcp_server = os.getenv("URL_MCP_SERVER")
        self.anthropic_model = os.getenv("ANTHROPIC_MODEL")
        self.max_tokens_model = int(os.getenv("MAX_TOKENS_MODEL", 1024))

    async def load_mcp_components(self, session: types.InitializeResult):
        """
        Load tools, prompts, and resources in the session dictionary.
        Args:
            :param session: Initialized MCP server session.
        Returns:
            :None
        """
        try:
            tools_response = await session.list_tools()
            for tool in tools_response.tools:
                self.sessions[tool.name] = session
                self.available_tools.append(
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "input_schema": tool.inputSchema,
                    }
                )
            prompts_response = await session.list_prompts()
            if prompts_response and prompts_response.prompts:
                for prompt in prompts_response.prompts:
                    self.sessions[prompt.name] = session
                    self.available_prompts.append(
                        {
                            "name": prompt.name,
                            "description": prompt.description,
                            "arguments": prompt.arguments,
                        }
                    )
            resources_response = await session.list_resources()
            if resources_response and resources_response.resources:
                for resource in resources_response.resources:
                    resource_uri = str(resource.uri)
                    self.sessions[resource_uri] = session
        except Exception as ex:
            print(f"Error loading MCP component from session={session}: {ex}")

    async def connect_to_server(self, server_name, server_config):
        """
        Create connection and session from local or server file configuration.
        Args:
            :param server_name: MCP server name.
            :param server_config: server configuration.
        Returns:
            :None
        """
        try:
            if self.run_locally:
                server_params = StdioServerParameters(**server_config)
                transport = await self.exit_stack.enter_async_context(
                    stdio_client(server_params)
                )
                read, write = transport
            else:
                transport = await self.exit_stack.enter_async_context(
                    streamablehttp_client(url=server_config.get("endpoint"))
                )
                read, write, _ = transport

            session = await self.exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            await session.initialize()
            await self.load_mcp_components(session)
        except Exception as ex:
            print(f"Error connecting to server: {server_name}: {ex}")

    async def connect_to_servers(self):
        """
        Connect to all servers defined in the local or server configuration file.
        """
        try:
            servers = self.connectors_config.get("mcpServers", {})
            for server_name, server_config in servers.items():
                await self.connect_to_server(server_name, server_config)
        except Exception as ex:
            raise Exception(f"Error loading server config: {ex}")

    async def process_query(self, query):
        """
        Process user query using Anthropic API.
        Args:
            :param query: user query.
        Returns:
            :Print query answer.
        """
        messages = [{"role": "user", "content": query}]
        while True:
            response = self.anthropic.messages.create(
                max_tokens=self.max_tokens_model,
                model=self.anthropic_model,
                tools=self.available_tools,
                messages=messages,
            )
            assistant_content = []
            has_tool_use = False
            for content in response.content:
                if content.type == "text":
                    print(content.text)
                    assistant_content.append(content)
                elif content.type == "tool_use":
                    has_tool_use = True
                    assistant_content.append(content)
                    messages.append({"role": "assistant", "content": assistant_content})
                    # Get session and call tool
                    session = self.sessions.get(content.name)
                    if not session:
                        print(f"Tool '{content.name}' not found.")
                        break
                    result = await session.call_tool(
                        content.name, arguments=content.input
                    )
                    messages.append(
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": content.id,
                                    "content": result.content,
                                }
                            ],
                        }
                    )
            if not has_tool_use:
                break

    async def get_resource(self, resource_uri: str):
        """
        Get resource content from MCP session.
        Args:
            :param resource_uri: resource URI.
        Returns:
            :Print resource content.
        """
        session = self.sessions.get(resource_uri)
        if not session and resource_uri.startswith("papers://"):
            for uri, sess in self.sessions.items():
                if uri.startswith("papers://"):
                    session = sess
                    break
        if not session:
            print(f"Resource '{resource_uri}' not found.")
            return
        try:
            result = await session.read_resource(uri=resource_uri)
            if result and result.contents:
                print(f"\nResource: {resource_uri}")
                print("Content:")
                print(result.contents[0].text)
            else:
                print("No content available.")
        except Exception as ex:
            print(f"Error getting resource={resource_uri}: {ex}")

    async def list_prompts(self):
        """
        List all available prompts.
        """
        if not self.available_prompts:
            print("No prompts available.")
            return
        print("\nAvailable prompts:")
        for prompt in self.available_prompts:
            print(f"- {prompt['name']}: {prompt['description']}")
            if prompt["arguments"]:
                print("  Arguments:")
                for arg in prompt["arguments"]:
                    arg_name = arg.name if hasattr(arg, "name") else arg.get("name", "")
                    print(f"    - {arg_name}")

    async def execute_prompt(self, prompt_name: str, args: dict[(str, str)]):
        """
        Execute a prompt with the given arguments.
        Args:
            :param prompt_name: resource URI.
        Returns:
            :Print resource content.
        """
        session = self.sessions.get(prompt_name)
        if not session:
            print(f"Prompt '{prompt_name}' not found.")
            return
        try:
            result = await session.get_prompt(prompt_name, arguments=args)
            if result and result.messages:
                prompt_content = result.messages[0].content
                if isinstance(prompt_content, str):
                    text = prompt_content
                elif hasattr(prompt_content, "text"):
                    text = prompt_content.text
                else:
                    # Handle list of content items
                    text = " ".join(
                        item.text if hasattr(item, "text") else str(item)
                        for item in prompt_content
                    )
                print(f"\nExecuting prompt '{prompt_name}'...")
                await self.process_query(text)
        except Exception as e:
            print(f"Error executing prompt={prompt_name}: {e}")

    async def chat_loop(self):
        print(
            "\nHello! I'm here to help you search for academic papers "
            "on arXiv or extract information about specific papers."
        )
        print("(Write 'quit' to exit.)")
        print("\nUse: @papers to see available papers topics.")
        print("Use: @<topic> to search papers in that topic.")
        print("Use: /prompts to list available prompts.")
        print("Use: /prompt <prompt name> <arg1=value1> to execute a prompt.")
        while True:
            try:
                query = input("\nSend a message: ").strip()
                if not query:
                    continue
                if query.lower() == "quit":
                    break
                if query.startswith("@"):
                    topic = query[1:]
                    if topic == "papers":
                        resource_uri = "papers://folders"
                    else:
                        resource_uri = f"papers://{topic}"
                    await self.get_resource(resource_uri)
                    continue
                if query.startswith("/"):
                    parts = query.split()
                    command = parts[0].lower()
                    if command == "/prompts":
                        await self.list_prompts()
                    elif command == "/prompt":
                        if len(parts) < 2:
                            print("Usage: /prompt <name> <arg1=value1> <arg2=value2>")
                            continue
                        prompt_name = parts[1]
                        args = {}
                        for arg in parts[2:]:
                            if "=" in arg:
                                key, value = arg.split("=", 1)
                                args[key] = value
                        await self.execute_prompt(prompt_name, args)
                    else:
                        print(f"Unknown command: {command}")
                    continue
                await self.process_query(query)
            except Exception as e:
                print(f"\nError: {str(e)}")

    async def cleanup(self):
        """
        Closing MCP connections before exiting.
        """
        await self.exit_stack.aclose()


class ClientApplication:
    def __init__(self, run_locally, connectors_config_file):
        """
        Initialize the client application.
        """
        self.run_locally = run_locally
        self.connectors_config = get_app_config_parameters(connectors_config_file)

    async def run(self):
        """
        Run the client application.
        """
        chatbot = McpChatBot(self.run_locally, self.connectors_config)
        try:
            await chatbot.connect_to_servers()
            await chatbot.chat_loop()
        finally:
            await chatbot.cleanup()


if __name__ == "__main__":
    run_locally = (
        True if os.getenv("RUN_LOCALLY", "True") in ["True", "true", True] else False
    )
    if run_locally:
        nest_asyncio.apply()
        connectors_config_file = os.getenv("LOCAL_CONFIG_FILE")
    else:
        connectors_config_file = os.getenv("SERVER_CONFIG_FILE")
    asyncio.run(ClientApplication(run_locally, connectors_config_file).run())
