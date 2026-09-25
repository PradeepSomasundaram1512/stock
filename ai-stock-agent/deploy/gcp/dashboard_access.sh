#!/bin/bash
#
# Who may sign in to the dashboard: the invite list in gs://<project>-stock-dashboard-config/allowed_emails.json.
# Nobody is allowed unless listed. Changes take effect within about a minute, including for people
# already signed in (the app re-checks the list on every request).
#
#   ./deploy/gcp/dashboard_access.sh list
#   ./deploy/gcp/dashboard_access.sh invite tester@gmail.com
#   ./deploy/gcp/dashboard_access.sh revoke tester@gmail.com
cd "$(dirname "$0")"
source ./config.sh
FILE="gs://${PROJECT_ID}-stock-dashboard-config/allowed_emails.json"
ACTION="${1:-list}"; EMAIL="${2:-}"

CURRENT=$(gcloud storage cat "$FILE" 2>/dev/null || echo '[]')
if [ "$ACTION" = "list" ]; then
    echo "$CURRENT" | python3 -c "import json,sys; print('\n'.join(json.load(sys.stdin)) or '(nobody)')"
    exit
fi
case "$ACTION" in invite|revoke) ;; *) echo "usage: $0 list | invite EMAIL | revoke EMAIL"; exit 1 ;; esac
[ -z "$EMAIL" ] && { echo "usage: $0 $ACTION EMAIL"; exit 1; }
case "$EMAIL" in *@*.*) ;; *) echo "'$EMAIL' does not look like an email address"; exit 1 ;; esac

echo "$CURRENT" | ACTION="$ACTION" EMAIL="$EMAIL" python3 -c "
import json,os,sys
emails=sorted({e.lower() for e in json.load(sys.stdin)})
e=os.environ['EMAIL'].strip().lower()
emails = sorted(set(emails)|{e}) if os.environ['ACTION']=='invite' else [x for x in emails if x!=e]
print(json.dumps(emails))" | gcloud storage cp - "$FILE" >/dev/null && echo "✓ $ACTION $EMAIL" && "$(cd "$(dirname "$0")" && pwd)/dashboard_access.sh" list
