import argparse
import getpass
import os
import sys

import httpx


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate invite code via API")
    parser.add_argument("--base-url", help="Staging base URL (e.g. https://staging.example.com)")
    parser.add_argument("--username", help="Admin username")
    parser.add_argument("--password", help="Admin password (discouraged; use prompt/env)")
    parser.add_argument("--code", help="Optional invite code to set")
    parser.add_argument("--timeout", type=float, default=10.0, help="HTTP timeout in seconds")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    base_url = args.base_url or os.getenv("DMO_BASE_URL")
    username = args.username or os.getenv("DMO_ADMIN_USER")
    password = args.password or os.getenv("DMO_ADMIN_PASS")

    if not base_url:
        print("Error: --base-url or DMO_BASE_URL is required", file=sys.stderr)
        sys.exit(1)
    if not username:
        print("Error: --username or DMO_ADMIN_USER is required", file=sys.stderr)
        sys.exit(1)

    if not password:
        password = getpass.getpass("Admin password: ")

    login_payload = {"username": username, "password": password}

    with httpx.Client(timeout=args.timeout) as client:
        login_resp = client.post(f"{base_url}/api/auth/login", json=login_payload)
        if login_resp.status_code >= 400:
            print(f"Login failed: {login_resp.status_code} {login_resp.text}", file=sys.stderr)
            sys.exit(1)

        token = login_resp.json().get("access_token")
        if not token:
            print("Login failed: missing access_token", file=sys.stderr)
            sys.exit(1)

        invite_payload = {}
        if args.code:
            invite_payload["code"] = args.code

        invite_resp = client.post(
            f"{base_url}/api/auth/invite/generate",
            json=invite_payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        if invite_resp.status_code >= 400:
            print(f"Invite failed: {invite_resp.status_code} {invite_resp.text}", file=sys.stderr)
            sys.exit(1)

        code = invite_resp.json().get("code")
        if not code:
            print("Invite failed: missing code in response", file=sys.stderr)
            sys.exit(1)

        print(f"Invite Code Generated: {code}")


if __name__ == "__main__":
    main()
