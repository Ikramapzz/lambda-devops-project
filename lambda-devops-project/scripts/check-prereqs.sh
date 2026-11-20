#!/usr/bin/env bash
# Checks that every tool you need for this project is installed.
ok=1
check() {
  if command -v "$1" >/dev/null 2>&1; then
    printf "  [ok]      %-10s %s\n" "$1" "$($1 $2 2>&1 | head -n1)"
  else
    printf "  [MISSING] %-10s %s\n" "$1" "$3"
    ok=0
  fi
}
echo "Checking prerequisites..."
check python3 --version "Install Python 3.12+ from python.org"
check aws --version "Install AWS CLI v2: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
check sam --version "Install AWS SAM CLI: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html"
check git --version "Install Git from git-scm.com"
check docker --version "(optional) Install Docker Desktop - only needed for 'sam local'"
echo
if aws sts get-caller-identity >/dev/null 2>&1; then
  echo "AWS credentials: OK"
  aws sts get-caller-identity --query Arn --output text
else
  echo "AWS credentials: NOT configured - run 'aws configure'"
  ok=0
fi
[ "$ok" = 1 ] && echo "All good - you're ready." || echo "Fix the items above, then re-run."
