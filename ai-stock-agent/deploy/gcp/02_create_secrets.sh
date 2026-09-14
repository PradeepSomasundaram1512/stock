#!/bin/bash
#
# Push every key in your local .env into Secret Manager, one secret per key
# (secret ID == env var name, e.g. OPENAI_API_KEY). Re-run any time you
# rotate a key — it adds a new secret version rather than duplicating.
#
# Values are piped straight from .env to `gcloud secrets` and are never
# echoed to the terminal or logged.
#
# Usage:
#   export PROJECT_ID=your-gcp-project-id
#   ./deploy/gcp/02_create_secrets.sh
#
cd "$(dirname "$0")"
source ./config.sh
cd ../..   # back to ai-stock-agent/

ENV_FILE=".env"
if [ ! -f "$ENV_FILE" ]; then
    echo "Error: $ENV_FILE not found in $(pwd)"
    exit 1
fi

echo "========================================="
echo "Pushing .env values to Secret Manager"
echo "========================================="
echo ""

while IFS='=' read -r key value; do
    # skip blanks and comments
    [ -z "$key" ] && continue
    case "$key" in \#*) continue ;; esac

    # strip surrounding quotes from the value, if any
    value="${value%\"}"
    value="${value#\"}"
    value="${value%\'}"
    value="${value#\'}"

    if [ -z "$value" ]; then
        echo "  skip $key (empty)"
        continue
    fi

    if gcloud secrets describe "$key" >/dev/null 2>&1; then
        printf '%s' "$value" | gcloud secrets versions add "$key" --data-file=- >/dev/null
        echo "  updated $key"
    else
        printf '%s' "$value" | gcloud secrets create "$key" --data-file=- --replication-policy=automatic >/dev/null
        echo "  created $key"
    fi

    gcloud secrets add-iam-policy-binding "$key" \
        --member="serviceAccount:${RUN_SA_EMAIL}" \
        --role="roles/secretmanager.secretAccessor" \
        --condition=None >/dev/null
done < "$ENV_FILE"

echo ""
echo "✓ Secrets pushed. Next: ./deploy/gcp/03_build_and_push.sh"
