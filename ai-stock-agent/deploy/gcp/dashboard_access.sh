#!/bin/bash
#
# Who may sign in to the dashboard (Google sign-in via Cloud Run IAP). Nobody is allowed
# unless listed here; there is no public access.
#
#   ./deploy/gcp/dashboard_access.sh list
#   ./deploy/gcp/dashboard_access.sh invite tester@gmail.com
#   ./deploy/gcp/dashboard_access.sh revoke tester@gmail.com
#
# Uses the IAP REST API directly (the `gcloud beta iap` route prompts to install a component).
SELF="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"
cd "$(dirname "$0")"
source ./config.sh
SERVICE="stock-dashboard"
NUM=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
RES="projects/${NUM}/iap_web/cloud_run-${REGION}/services/${SERVICE}"
API="https://iap.googleapis.com/v1/${RES}"
TOKEN=$(gcloud auth print-access-token)
call() { curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -H "x-goog-user-project: $PROJECT_ID" -d "$2" "${API}:$1"; }

ACTION="${1:-list}"; EMAIL="${2:-}"
POLICY=$(call getIamPolicy '{}')
if [ "$ACTION" = "list" ]; then
    echo "$POLICY" | python3 -c "
import json,sys; p=json.load(sys.stdin)
if 'error' in p: sys.exit(p['error']['message'])
m=[x for b in p.get('bindings',[]) if b['role']=='roles/iap.httpsResourceAccessor' for x in b['members']]
print('\n'.join(m) or '(nobody)')"
    exit
fi
[ -z "$EMAIL" ] && { echo "usage: $0 invite|revoke EMAIL"; exit 1; }
NEW=$(echo "$POLICY" | ACTION="$ACTION" EMAIL="$EMAIL" python3 -c "
import json,os,sys; p=json.load(sys.stdin)
if 'error' in p: sys.exit(p['error']['message'])
role='roles/iap.httpsResourceAccessor'; who='user:'+os.environ['EMAIL'].lower()
b=next((b for b in p.setdefault('bindings',[]) if b['role']==role), None)
if b is None: b={'role':role,'members':[]}; p['bindings'].append(b)
if os.environ['ACTION']=='invite' and who not in b['members']: b['members'].append(who)
if os.environ['ACTION']=='revoke' and who in b['members']: b['members'].remove(who)
p['bindings']=[x for x in p['bindings'] if x['members']]
print(json.dumps({'policy':p}))") || exit 1
call setIamPolicy "$NEW" >/dev/null && echo "✓ $ACTION $EMAIL" && "$SELF" list
