# Airbnb MCP HTTP Wrapper
# Uses Node.js for the MCP server and Python for the HTTP wrapper

FROM node:20-slim

WORKDIR /app

# Install Python for the HTTP wrapper
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment and install Python dependencies
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy configuration and application files
COPY config.yml .
COPY src/ ./src/

# Pre-install the Airbnb MCP server package
RUN npm install -g @openbnb/mcp-server-airbnb

# Expose the HTTP port
EXPOSE 3038

# Run the HTTP wrapper server
CMD ["python", "src/http_server.py"]
