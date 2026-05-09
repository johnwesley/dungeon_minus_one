"""Manage staging DNS A record in DNSimple.

Usage:
    python scripts/manage_dns.py upsert --ip 1.2.3.4 [--ttl 300]
    python scripts/manage_dns.py delete
"""

import argparse
import os
import sys

import httpx

ZONE = "dungeonminusone.com"
RECORD_NAME = "staging"
RECORD_TYPE = "A"
BASE_URL = "https://api.dnsimple.com/v2"


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _get_record(client: httpx.Client, account_id: str) -> dict | None:
    """Fetch the existing A record for staging, or None."""
    resp = client.get(
        f"{BASE_URL}/{account_id}/zones/{ZONE}/records",
        params={"name": RECORD_NAME, "type": RECORD_TYPE},
    )
    resp.raise_for_status()
    records = resp.json()["data"]
    return records[0] if records else None


def upsert(client: httpx.Client, account_id: str, ip: str, ttl: int) -> int:
    record = _get_record(client, account_id)

    if record is None:
        print(f"Creating {RECORD_NAME}.{ZONE} A {ip} (TTL {ttl})")
        resp = client.post(
            f"{BASE_URL}/{account_id}/zones/{ZONE}/records",
            json={"name": RECORD_NAME, "type": RECORD_TYPE, "content": ip, "ttl": ttl},
        )
        resp.raise_for_status()
        print("Record created.")
        return 0

    if record["content"] == ip and record["ttl"] == ttl:
        print(f"{RECORD_NAME}.{ZONE} already points to {ip} (TTL {ttl}), no update needed.")
        return 0

    record_id = record["id"]
    print(f"Updating {RECORD_NAME}.{ZONE} -> {ip} (TTL {ttl})")
    resp = client.patch(
        f"{BASE_URL}/{account_id}/zones/{ZONE}/records/{record_id}",
        json={"content": ip, "ttl": ttl},
    )
    resp.raise_for_status()
    print("Record updated.")
    return 0


def delete(client: httpx.Client, account_id: str) -> int:
    record = _get_record(client, account_id)

    if record is None:
        print(f"No {RECORD_NAME}.{ZONE} A record found, nothing to delete.")
        return 0

    record_id = record["id"]
    print(f"Deleting {RECORD_NAME}.{ZONE} A record (id={record_id})")
    resp = client.delete(
        f"{BASE_URL}/{account_id}/zones/{ZONE}/records/{record_id}",
    )
    resp.raise_for_status()
    print("Record deleted.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage staging DNS A record in DNSimple.")
    sub = parser.add_subparsers(dest="command", required=True)

    upsert_p = sub.add_parser("upsert", help="Create or update the A record")
    upsert_p.add_argument("--ip", required=True, help="IPv4 address for the A record")
    upsert_p.add_argument("--ttl", type=int, default=300, help="TTL in seconds (default: 300)")

    sub.add_parser("delete", help="Delete the A record")

    args = parser.parse_args()

    token = os.environ.get("DNSIMPLE_TOKEN")
    account_id = os.environ.get("DNSIMPLE_ACCOUNT_ID")
    if not token or not account_id:
        print("Error: DNSIMPLE_TOKEN and DNSIMPLE_ACCOUNT_ID must be set.", file=sys.stderr)
        return 1

    client = httpx.Client(headers=_headers(token), timeout=30)
    try:
        if args.command == "upsert":
            return upsert(client, account_id, args.ip, args.ttl)
        elif args.command == "delete":
            return delete(client, account_id)
    finally:
        client.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
