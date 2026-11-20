# AWS Lambda DevOps Project - Zero to Hero

Build, test, deploy and operate a real serverless API on AWS, with a full CI/CD pipeline.

**What you will build**

```
 Developer ──git push──► GitHub Actions ──(OIDC, no keys)──► AWS
                           │ lint · validate · unit test
                           │ deploy dev → smoke test
                           │ manual approval
                           └ deploy prod (canary 10% / 5 min, auto-rollback)

 Client ─► API Gateway (HTTP API) ─► Lambda (Python 3.12, arm64) ─► DynamoDB
                                        │
                                        ├─ CloudWatch Logs (14-day retention)
                                        ├─ X-Ray tracing
                                        └─ CloudWatch Alarms ─► SNS ─► your email
```

**Skills you'll practise:** Infrastructure as Code (AWS SAM/CloudFormation), unit and smoke testing, CI/CD, passwordless auth (OIDC), multi-stage environments, canary deployments, monitoring and alerting, cost control, cleanup.

**Cost:** everything fits comfortably in the AWS free tier / pennies. Lambda, API Gateway, DynamoDB (on-demand) and CloudWatch cost close to nothing at tutorial traffic. Always do **Part 10 (cleanup)** when done.

**Time:** about 2-3 hours.

---

## Project layout

```
lambda-devops-project/
├── src/app.py                      # Lambda function code
├── src/requirements.txt            # runtime deps (none needed)
├── template.yaml                   # ALL infrastructure (SAM)
├── samconfig.toml                  # dev / prod deploy settings
├── tests/unit/                     # fast tests, DynamoDB mocked with moto
├── tests/integration/test_api.py   # smoke test against a live URL
├── iam/github-oidc.yaml            # one-time role for GitHub Actions
├── .github/workflows/ci-cd.yml     # the pipeline
├── scripts/check-prereqs.sh        # verifies your tools
├── Makefile                        # shortcuts (make test, make deploy-dev ...)
└── docs/TROUBLESHOOTING.md
```

---

## Part 0 - Create and secure your AWS account

1. Go to <https://aws.amazon.com> and create an account (needs a card; free tier applies).
2. **Secure the root user:** sign in as root, enable MFA (Account name menu → Security credentials → Assign MFA device).
3. **Set a budget alarm** so you never get a surprise bill: Billing → Budgets → Create budget → *Zero spend budget* (or a USD 5 monthly budget) → add your email.
4. **Create a day-to-day admin user** (don't use root):
   - IAM → Users → Create user → name `devops-learner`
   - Permissions: attach `AdministratorAccess` (fine for a personal learning account)
   - Open the user → Security credentials → Create access key → "Command Line Interface" → download the CSV.
   - Enable MFA on this user too.
5. Pick a region. This guide uses **ap-south-1 (Mumbai)**. If you pick another, change it in `samconfig.toml`, `Makefile`, and the `AWS_REGION` GitHub variable.

---

## Part 1 - Install your tools

| Tool | Why | Install |
|---|---|---|
| Python 3.12+ | code + tests | <https://www.python.org/downloads/> |
| Git | version control | <https://git-scm.com> |
| AWS CLI v2 | talk to AWS | <https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html> |
| AWS SAM CLI | build and deploy serverless apps | <https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html> |
| Docker (optional) | only for `sam local` | <https://www.docker.com/products/docker-desktop/> |
| GitHub account | CI/CD | <https://github.com> |

Configure the AWS CLI with the access key from Part 0:

```bash
aws configure
# AWS Access Key ID:     <from CSV>
# AWS Secret Access Key: <from CSV>
# Default region name:   ap-south-1
# Default output format: json
```

Verify everything:

```bash
unzip lambda-devops-project.zip && cd lambda-devops-project
bash scripts/check-prereqs.sh
```

You should see all `[ok]` and your IAM user ARN.

---

## Part 2 - Understand the code

Open these three files and read them once before running anything.

**`src/app.py`** - one Lambda function that handles five routes. API Gateway (HTTP API, payload v2) puts the matched route in `event["routeKey"]`, and `ROUTES` maps that to a Python function. Notes:
- The DynamoDB client is created lazily and reused across warm invocations (faster, cheaper).
- Input is validated (`name` required) and errors return proper HTTP codes (400/404/500).
- Unhandled errors are logged with a stack trace so you can find them in CloudWatch.

**`template.yaml`** - the whole infrastructure as code:
- `ItemsTable` - DynamoDB, on-demand billing, encrypted; in prod it is *retained* if the stack is deleted and has point-in-time recovery.
- `ItemsApi` + `ApiFunction` events - API Gateway routes.
- `ApiFunction` - Lambda with least-privilege access to *only* that table (`DynamoDBCrudPolicy`), X-Ray on, arm64 (cheaper), `AutoPublishAlias: live` for versioned deployments.
- `DeploymentPreference` - in **prod** a canary: 10% of traffic for 5 minutes, then 100%. If `ErrorsAlarm` fires, CodeDeploy automatically rolls back.
- `ApiFunctionLogGroup` - logs kept 14 days (otherwise they live forever and cost money).
- `AlarmTopic`, `ErrorsAlarm`, `ThrottlesAlarm` - monitoring.

**`samconfig.toml`** - saved deploy settings so `sam deploy --config-env dev` needs no questions.

---

## Part 3 - Run the tests locally

```bash
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

pytest -v          # 8 unit tests, DynamoDB is faked by moto - no AWS needed
ruff check src tests
cfn-lint template.yaml
```

All three should pass. (`make install`, `make test`, `make lint` do the same.)

**Optional - run the API on your laptop (needs Docker):**

```bash
sam build
sam local start-api
curl http://127.0.0.1:3000/health
```
`/health` works locally; `/items` routes need a real table, so test those after deploying.

---

## Part 4 - First deployment (dev), by hand

Deploying by hand first teaches you what the pipeline will automate later.

```bash
sam build                       # packages src/ into .aws-sam/build
sam deploy --config-env dev     # creates the CloudFormation stack
```

The first deploy takes 2-4 minutes. SAM creates a managed S3 bucket for artifacts automatically (`resolve_s3 = true`).

At the end you'll see **Outputs**. Copy `ApiUrl`, or fetch it any time:

```bash
API=$(aws cloudformation describe-stacks --stack-name lambda-devops-dev \
  --region ap-south-1 \
  --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" --output text)
echo $API
```

---

## Part 5 - Try the API

```bash
curl $API/health

curl -X POST $API/items -H "Content-Type: application/json" \
  -d '{"name":"My first item","description":"hello lambda"}'

curl $API/items

# use an id from the POST response:
curl $API/items/<id>
curl -X DELETE $API/items/<id> -i       # expect HTTP 204
curl -X POST $API/items -d '{}' -H "Content-Type: application/json"   # expect 400
```

Run the automated smoke test (the same one CI runs):

```bash
API_URL=$API python3 tests/integration/test_api.py
```

---

## Part 6 - Observability (see inside your system)

1. **Logs:** `make logs-dev` (or `sam logs --stack-name lambda-devops-dev --region ap-south-1 --tail`), then call the API in another terminal and watch requests appear.
2. **Console tour** (Region ap-south-1):
   - Lambda → your function → *Monitor* tab (invocations, duration, errors)
   - CloudWatch → Log groups → `/aws/lambda/lambda-devops-dev-ApiFunction-...`
   - CloudWatch → X-Ray traces → Traces (request waterfall: API → Lambda → DynamoDB)
   - CloudWatch → Alarms (`ErrorsAlarm`, `ThrottlesAlarm`)
   - DynamoDB → Tables → Explore items
3. **Enable alert emails:**
   ```bash
   sam deploy --config-env dev --parameter-overrides Stage=dev AlarmEmail=you@example.com
   ```
   Confirm the subscription email from AWS. Now break the function on purpose (e.g. temporarily add `raise Exception("boom")` at the top of `lambda_handler`, rebuild, redeploy, call the API) and watch the alarm email arrive. Revert the change afterwards.

---

## Part 7 - CI/CD with GitHub Actions (passwordless)

The pipeline logs in to AWS using **OIDC**: GitHub proves who it is with a short-lived token, AWS hands out temporary credentials. There are no access keys stored in GitHub.

**7.1 Create the GitHub repo and push the code**

```bash
git init -b main
git add .
git commit -m "Initial commit"
# create an empty repo named lambda-devops-project on github.com, then:
git remote add origin https://github.com/<YOUR_USER>/lambda-devops-project.git
git push -u origin main
```
(The first run will fail at the AWS steps - that's expected until 7.2-7.3 are done.)

**7.2 Deploy the OIDC role (once, manually)**

```bash
aws cloudformation deploy \
  --stack-name github-oidc-lambda-devops \
  --template-file iam/github-oidc.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --region ap-south-1 \
  --parameter-overrides GitHubOrg=<YOUR_GITHUB_USER> GitHubRepo=lambda-devops-project

aws cloudformation describe-stacks --stack-name github-oidc-lambda-devops \
  --region ap-south-1 --query "Stacks[0].Outputs[0].OutputValue" --output text
```
Copy the role ARN it prints. (If you get "provider already exists", re-run with `CreateOIDCProvider=false`.)

**7.3 Configure GitHub**

Repo → Settings → Secrets and variables → Actions → **Variables** tab → New repository variable:
- `AWS_ROLE_ARN` = the ARN from 7.2
- `AWS_REGION` = `ap-south-1`

Repo → Settings → **Environments**:
- create `dev` (no rules)
- create `production` → enable **Required reviewers** → add yourself. This is your manual approval gate. (On free private repos, environment protection may be limited; public repos have it.)

**7.4 Watch the pipeline work**

Create a feature branch and open a pull request:

```bash
git checkout -b feature/add-description-limit
# make a small change in src/app.py, e.g. reject descriptions longer than 200 chars
# add a unit test for it in tests/unit/test_app.py
git commit -am "Limit description length"
git push -u origin feature/add-description-limit
```
Open a PR on GitHub. Only the **test** job runs (lint, cfn-lint, pytest, sam build). Merge it, and on `main` the full flow runs:

1. `test` → 2. `deploy-dev` → 3. `integration-dev` (smoke test the live dev API) → 4. waits for your approval → 5. `deploy-prod` (canary) → 6. `smoke-prod`.

Click **Review deployments → Approve** when prompted. After it finishes, the prod stack is `lambda-devops-prod`.

---

## Part 8 - Canary deployments and rollbacks (the "hero" part)

1. In the AWS console open **CodeDeploy → Deployments** while a prod deploy is running. You'll see traffic shift: 10% to the new version for 5 minutes, then 100%.
2. **Test automatic rollback:** push a change that makes the function throw errors (e.g. `raise Exception("boom")` in `health`), let it reach prod, and hit `/health` repeatedly during the canary window:
   ```bash
   PROD=$(aws cloudformation describe-stacks --stack-name lambda-devops-prod --region ap-south-1 \
     --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" --output text)
   for i in $(seq 1 60); do curl -s -o /dev/null -w "%{http_code}\n" $PROD/health; sleep 3; done
   ```
   `ErrorsAlarm` goes to ALARM, CodeDeploy shifts traffic back to the old version, and the deployment shows **Rolled back**. Users saw errors on at most 10% of requests, for a short time.
3. **Manual rollback of a bad release:** revert the commit (`git revert <sha> && git push`) - the pipeline redeploys the previous code. This is the normal, auditable way to roll back.

---

## Part 9 - Hardening checklist (next steps)

You now have a working pipeline. For real production work, add:

- **Separate AWS accounts** for dev and prod (AWS Organizations) with a role per account.
- **Tighten the OIDC role policy** in `iam/github-oidc.yaml` to specific resource ARNs.
- **Auth on the API:** JWT authorizer (Cognito) or IAM auth on the HTTP API.
- **WAF / custom domain** (Route 53 + ACM) in front of API Gateway.
- **Secrets** in AWS Secrets Manager or SSM Parameter Store, never in code.
- **Dead-letter queues / retries** for async invocations; **reserved concurrency** to protect downstream systems.
- **Structured logging + metrics** with AWS Lambda Powertools.
- **Security scanning** in CI (`pip-audit`, `bandit`, Dependabot).
- **Code signing / SBOM** if your org requires it.
- Rewrite the infrastructure in **Terraform** or **AWS CDK** to compare tools.

---

## Part 10 - Clean up (important!)

```bash
make delete-dev       # or: sam delete --stack-name lambda-devops-dev --region ap-south-1
make delete-prod      # prod table is RETAINED by design; delete it in the DynamoDB console

aws cloudformation delete-stack --stack-name github-oidc-lambda-devops --region ap-south-1
```
Also delete the SAM-managed artifact bucket if you want a totally clean account:
S3 → bucket starting with `aws-sam-cli-managed-default` → empty → delete (after deleting the `aws-sam-cli-managed-default` stack in CloudFormation).

Confirm in **Billing → Bills** that nothing is still running.

---

## Command cheat sheet

| Task | Command |
|---|---|
| Run unit tests | `make test` |
| Lint and validate | `make lint` |
| Build | `sam build` |
| Deploy dev / prod | `make deploy-dev` / `make deploy-prod` |
| Smoke test dev | `make smoke-dev` |
| Tail logs | `make logs-dev` |
| Invoke locally | `sam local invoke ApiFunction -e event.json` |
| List stacks | `aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE` |
| Delete dev | `make delete-dev` |

Stuck? See `docs/TROUBLESHOOTING.md`.
