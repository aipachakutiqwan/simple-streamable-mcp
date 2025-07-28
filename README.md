# simple-streamable-mcp

Welcome to the lightweight Streamable MCP client-server chatbot powered by Anthropic Claude as the LLM backend.

## ⚡ Introduction

This repository provides a simple implementation of a streamable MCP client-server chatbot that uses Anthropic Claude as the LLM backend. The chatbot is designed to answer questions about research papers on arXiv or extract specific information from them.


:heavy_exclamation_mark: **This repository code is not intended for direct use in production**. Do not use it as-is. It serves as a reference implementation. You should review the logic, refactor the code to fit your requirements, and write appropriate unit tests before considering it for any production deployment.



## :rocket: Setup

### 🌱  Create an environment and install dependencies

Check out the Contributing guide to learn how to set up the environment, install dependencies, and get started contributing to this repository.

### 🌱 Setting up env variables
You can use `.env` file for set the following enviromental variables.
```
export ANTHROPIC_API_KEY=SET_YOUR_API_KEY_HERE
export SERVER_CONFIG_FILE=config/server_config.yaml
export LOCAL_CONFIG_FILE=config/local_config.yaml
export LOG_CONFIG_FILE=config/log_config.yaml
export RUN_LOCALLY=False
export PORT=8001
export ANTHROPIC_MODEL=claude-3-7-sonnet-20250219
export MAX_TOKENS_MODEL=2024

```

### 🌱 Antrophic Claude API
* Sign up [here](https://console.anthropic.com/settings/keys) and set `ANTHROPIC_API_KEY` in your environment.


## ✅ How to Use

:pushpin: Locally

This version initializes the chatbot and creates an MCP instance locally using the local configuration file.
```
export RUN_LOCALLY=True
python src/client/mcp_chatbot.py
```

:pushpin: Client/Server

This version starts the MPC server and initializes an MCP client chatbot to communicate with it. Follow the next 2 steps to activate the Client/Server option.

Launch a terminal session and activate the MCP server.
```
export RUN_LOCALLY=False
python src/server/mcp_server.py
```
Open a new terminal and start the MCP client.
```
export RUN_LOCALLY=False
python src/client/mcp_chatbot.py
```

:pushpin: MCP Inspector
Enables activation of the MCP inspector interface for interaction with the MCP server.

Execute the following command, setting the STDIO parameters to establish a connection with the MCP server.

```
mcp dev src/server/mcp_server.py
```

- Transport type: STDIO
- Command: uv
- Arguments: run --with mcp mcp run src/server/mcp_server.py
