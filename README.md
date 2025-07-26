# mcp-course

1. Simple MCP server
mcp dev src/server.py 

Transport type: STDIO
Command: uv
Arguments: run --with mcp mcp run src/server.py

2. MCP and Gradio integration

python src/gradio_mcp_server.py 

MCP Chatbot
1. Server
npx @modelcontextprotocol/inspector uv run src/mcp_chatbot/research_server.py

2. Client
uv run src/mcp_chatbot/mcp_chatbot.py 
uv run src/mcp_chatbot/connect_mcp_chatbot.py 

