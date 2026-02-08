#!/usr/bin/env bash
# Create the "company" index in OpenSearch with mappings from company-index.json
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
# .env is at project root
set -a && source "$SCRIPT_DIR/../.env" 2>/dev/null && set +a
PASSWORD="${OPENSEARCH_INITIAL_ADMIN_PASSWORD:?Set OPENSEARCH_INITIAL_ADMIN_PASSWORD in .env}"
curl -k -s -X PUT "https://localhost:9201/company" \
  -u "admin:$PASSWORD" \
  -H "Content-Type: application/json" \
  -d @"company-index.json"
