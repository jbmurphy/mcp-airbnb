#!/usr/bin/env python3
"""
Generic MCP HTTP Wrapper
Wraps any stdio-based MCP server and exposes it via HTTP REST API
"""
import os
import asyncio
import threading
import yaml
from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from contextlib import AsyncExitStack

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Create a persistent event loop in a background thread
_loop = None
_loop_thread = None

def get_event_loop():
    """Get or create the persistent event loop"""
    global _loop, _loop_thread
    if _loop is None or not _loop.is_running():
        _loop = asyncio.new_event_loop()
        _loop_thread = threading.Thread(target=_loop.run_forever, daemon=True)
        _loop_thread.start()
    return _loop

def run_async(coro):
    """Run an async coroutine in the persistent event loop"""
    loop = get_event_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result(timeout=120)  # 2 minute timeout

# Load configuration
def load_config():
    """Load configuration from config.yml or environment variables"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.yml')

    # Default configuration
    config = {
        'server': {
            'name': 'generic-mcp-server',
            'command': 'python',
            'args': ['server.py'],
            'env': {},
            'port': 3050
        }
    }

    # Try to load from config.yml
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                loaded_config = yaml.safe_load(f)
                if loaded_config:
                    config.update(loaded_config)
                    logger.info(f"Loaded configuration from {config_path}")
        except Exception as e:
            logger.warning(f"Failed to load config.yml: {e}, using defaults")

    # Override with environment variables if provided
    if os.getenv('MCP_COMMAND'):
        config['server']['command'] = os.getenv('MCP_COMMAND')
    if os.getenv('MCP_ARGS'):
        import json
        config['server']['args'] = json.loads(os.getenv('MCP_ARGS'))
    if os.getenv('PORT'):
        config['server']['port'] = int(os.getenv('PORT'))

    return config

CONFIG = load_config()
PORT = CONFIG['server']['port']
SERVER_NAME = CONFIG['server']['name']

class MCPClient:
    """Generic client that communicates with any MCP server via stdio"""

    def __init__(self, command, args, env=None):
        self.command = command
        self.args = args
        self.env = env or {}
        self.session = None
        self.exit_stack = None

    async def _ensure_connection(self):
        """Ensure we have an active MCP session"""
        if self.session is None:
            logger.info(f"Starting MCP server: {self.command} {' '.join(self.args)}")

            # Set up environment variables
            server_env = os.environ.copy()
            server_env.update(self.env)

            # Create server parameters for stdio connection
            server_params = StdioServerParameters(
                command=self.command,
                args=self.args,
                env=server_env
            )

            # Create exit stack for managing async context managers
            self.exit_stack = AsyncExitStack()

            try:
                # Connect to server via stdio
                stdio_transport = await self.exit_stack.enter_async_context(
                    stdio_client(server_params)
                )
                read, write = stdio_transport

                # Create client session
                self.session = await self.exit_stack.enter_async_context(
                    ClientSession(read, write)
                )

                # Initialize the session
                await self.session.initialize()
                logger.info("MCP session initialized successfully")

            except Exception as e:
                logger.error(f"Failed to initialize MCP session: {e}")
                if self.exit_stack:
                    await self.exit_stack.aclose()
                    self.exit_stack = None
                self.session = None
                raise

    async def list_tools(self):
        """List all available tools"""
        await self._ensure_connection()
        result = await self.session.list_tools()
        return result

    async def call_tool(self, tool_name, arguments):
        """Call a specific tool"""
        await self._ensure_connection()
        result = await self.session.call_tool(tool_name, arguments)
        return result

    async def close(self):
        """Close the MCP session"""
        if self.exit_stack:
            await self.exit_stack.aclose()
        self.session = None
        self.exit_stack = None

# Global client instance
mcp_client = MCPClient(
    command=CONFIG['server']['command'],
    args=CONFIG['server']['args'],
    env=CONFIG['server']['env']
)

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": f"{SERVER_NAME}-http-wrapper",
        "mcp_server": {
            "command": CONFIG['server']['command'],
            "args": CONFIG['server']['args']
        }
    }), 200

@app.route('/mcp/list_tools', methods=['GET', 'POST'])
def list_tools():
    """List all available tools"""
    try:
        result = run_async(mcp_client.list_tools())

        # Convert MCP result to JSON-serializable format
        tools_list = [
            {
                "name": tool.name,
                "description": tool.description or "",
                "inputSchema": tool.inputSchema
            }
            for tool in result.tools
        ]

        return jsonify({"tools": tools_list}), 200

    except Exception as e:
        logger.error(f"Error listing tools: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/mcp/call_tool', methods=['POST'])
def call_tool():
    """Call a specific tool"""
    try:
        data = request.json
        tool_name = data.get('name')
        tool_args = data.get('arguments', {})

        if not tool_name:
            return jsonify({"error": "Tool name is required"}), 400

        result = run_async(mcp_client.call_tool(tool_name, tool_args))

        # Convert MCP result to JSON-serializable format
        content_list = [
            {
                "type": content.type,
                "text": content.text if hasattr(content, 'text') else str(content)
            }
            for content in result.content
        ]

        return jsonify({"content": content_list}), 200

    except Exception as e:
        logger.error(f"Error calling tool: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    logger.info(f"Starting {SERVER_NAME} HTTP Wrapper on port {PORT}")
    logger.info(f"MCP Server: {CONFIG['server']['command']} {' '.join(CONFIG['server']['args'])}")
    app.run(host='0.0.0.0', port=PORT, debug=False)
