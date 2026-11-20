# Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Unable to locate credentials` | AWS CLI not configured | `aws configure` (or `aws sso login`), then `aws sts get-caller-identity` |
| `sam: command not found` | SAM CLI not installed | Install it (see README Part 1), reopen the terminal |
| `Error: Failed to create changeset ... InsufficientCapabilities` | Missing IAM capability | `samconfig.toml` already sets `CAPABILITY_IAM`; make sure you pass `--config-env dev` |
| `ROLLBACK_COMPLETE` stack won't update | First deploy failed, stack is stuck | `sam delete --stack-name lambda-devops-dev --region ap-south-1`, fix the error, deploy again |
| `AccessDeniedException` during deploy | Your IAM user/role lacks permissions | Use an admin-capable learning user, or extend the policy |
| `{"message":"Internal Server Error"}` from curl | Lambda raised an error | `make logs-dev` and read the stack trace |
| `{"message":"Not Found"}` | Wrong URL (missing `/dev` stage) | Use the full `ApiUrl` output, e.g. `.../dev/health` |
| GitHub Action: `Not authorized to perform sts:AssumeRoleWithWebIdentity` | OIDC trust doesn't match your repo | Check `GitHubOrg`/`GitHubRepo` parameters in `iam/github-oidc.yaml` match exactly (case-sensitive) |
| GitHub Action: `Credentials could not be loaded` | `AWS_ROLE_ARN` variable missing | Add it under Settings -> Secrets and variables -> Actions -> **Variables** |
| `OIDC provider already exists` | Provider created earlier in this account | Redeploy the OIDC stack with `CreateOIDCProvider=false` |
| Prod deploy rolled back | Alarm fired during canary window | Check CodeDeploy console + CloudWatch alarm; fix the bug and redeploy |
| `sam local start-api` fails | Docker not running | Start Docker Desktop. Note: local mode has no real DynamoDB table |
| `pytest: ModuleNotFoundError: app` | Running from wrong folder | Run `pytest` from the project root (pytest.ini sets `pythonpath = src`) |
