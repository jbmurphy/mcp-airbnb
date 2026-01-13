# MCP Airbnb

MCP server for searching Airbnb listings and retrieving property details.

## Overview

This wraps the [@openbnb/mcp-server-airbnb](https://github.com/AkekaratP/mcp-server-airbnb) package using the generic HTTP wrapper pattern.

**Port:** 3041
**URL:** https://mcp-airbnb.local.jbmurphy.com

## Tools

| Tool | Description |
|------|-------------|
| `airbnb_search` | Search Airbnb listings with filters (location, dates, guests, price range) |
| `airbnb_listing_details` | Get detailed information about a specific property |

## Usage

### Search for listings

```bash
curl -X POST https://mcp-airbnb.local.jbmurphy.com/mcp/call_tool \
  -H "Content-Type: application/json" \
  -d '{
    "name": "airbnb_search",
    "arguments": {
      "location": "New York",
      "checkin": "2025-03-01",
      "checkout": "2025-03-05",
      "adults": 2
    }
  }'
```

### Get listing details

```bash
curl -X POST https://mcp-airbnb.local.jbmurphy.com/mcp/call_tool \
  -H "Content-Type: application/json" \
  -d '{
    "name": "airbnb_listing_details",
    "arguments": {
      "id": "12345678"
    }
  }'
```

## Build & Deploy

```bash
# Build locally
docker-compose up -d --build

# Or via main docker-compose
cd .. && docker-compose up -d --build mcp-airbnb
```

## Source

Based on https://github.com/AkekaratP/mcp-server-airbnb (MIT License)
