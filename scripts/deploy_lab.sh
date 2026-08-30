#!/usr/bin/env bash
# Get the auth lab onto a PUBLIC HTTPS URL. AgentCore Browser runs in an
# AWS-managed environment and cannot reach localhost (Section 11).
#
# This script does not assume a single deployment target because the doc
# leaves that choice open (Section 9 suggests Lambda Function URL / App
# Runner / any small AWS-backed host). Pick ONE of the options below,
# uncomment it, and fill in the blanks — or deploy however you're most
# comfortable; the only hard requirement is a public https:// URL that
# serves auth-lab/app.py.
set -euo pipefail

echo "Pick a deploy path for auth-lab/app.py (edit this script and uncomment one):"
echo

# --- Option A: AWS App Runner from source (simplest, ~5-10 min) -----------
# aws apprunner create-service \
#   --service-name keyper-auth-lab \
#   --source-configuration '{"CodeRepository":{"RepositoryUrl":"<your public git remote>","SourceCodeVersion":{"Type":"BRANCH","Value":"main"},"CodeConfiguration":{"ConfigurationSource":"API","CodeConfigurationValues":{"Runtime":"PYTHON_312","BuildCommand":"pip install -r auth-lab/requirements.txt","StartCommand":"uvicorn auth-lab.app:app --host 0.0.0.0 --port 8080","Port":"8080"}}}}'

# --- Option B: Lambda Function URL (needs Mangum to adapt FastAPI) --------
# pip install mangum -t auth-lab/build --break-system-packages
# cp auth-lab/app.py auth-lab/build/
# cd auth-lab/build && zip -r ../lab.zip . && cd -
# aws lambda create-function --function-name keyper-auth-lab \
#   --runtime python3.12 --handler app.handler \
#   --zip-file fileb://auth-lab/lab.zip \
#   --role <your-lambda-execution-role-arn>
# aws lambda create-function-url-config --function-name keyper-auth-lab --auth-type NONE

# --- Option C: any host you already use (Fly.io, Render, EC2, etc.) -------
# Just make sure `uvicorn auth-lab.app:app --host 0.0.0.0 --port <port>`
# is reachable over https:// and you're done.

echo "No option selected yet — this is intentional. Edit the script, or"
echo "run 'uvicorn auth-lab.app:app --reload --port 8090' locally first to"
echo "eyeball the pages before deploying."
