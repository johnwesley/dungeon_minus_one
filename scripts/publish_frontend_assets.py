#!/usr/bin/env python3
"""Upload frontend build assets to DigitalOcean Spaces.

Requires environment variables:
  SPACES_ACCESS_KEY
  SPACES_SECRET_KEY

Example:
  python scripts/publish_frontend_assets.py --dist frontend/dist \
    --space dungeon-minus-one-assets --region nyc3 --prefix staging/v0.6.2
"""

from __future__ import annotations

import argparse
import mimetypes
import os
from pathlib import Path

import boto3


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish frontend assets to Spaces.")
    parser.add_argument("--dist", default="frontend/dist", help="Path to Vite dist directory.")
    parser.add_argument("--space", required=True, help="Spaces bucket name.")
    parser.add_argument("--region", default="nyc3", help="Spaces region (default: nyc3).")
    parser.add_argument("--prefix", default="", help="Key prefix (e.g. staging/v0.6.2).")
    parser.add_argument(
        "--cache-control",
        default="public, max-age=31536000, immutable",
        help="Cache-Control header for assets.",
    )
    parser.add_argument(
        "--acl",
        default="public-read",
        help="ACL for uploaded objects (default: public-read).",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print uploads without sending.")
    return parser.parse_args()


def ensure_mime_types() -> None:
    mimetypes.add_type("application/javascript", ".js")
    mimetypes.add_type("application/javascript", ".mjs")
    mimetypes.add_type("text/css", ".css")
    mimetypes.add_type("image/svg+xml", ".svg")
    mimetypes.add_type("font/woff2", ".woff2")
    mimetypes.add_type("font/woff", ".woff")


def iter_asset_files(dist: Path) -> list[Path]:
    files: list[Path] = []
    for path in dist.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix == ".html":
            continue
        files.append(path)
    return files


def main() -> int:
    args = parse_args()
    dist = Path(args.dist).resolve()

    if not dist.exists():
        raise SystemExit(f"Dist folder not found: {dist}")

    access_key = os.environ.get("SPACES_ACCESS_KEY") or os.environ.get("AWS_ACCESS_KEY_ID")
    secret_key = os.environ.get("SPACES_SECRET_KEY") or os.environ.get("AWS_SECRET_ACCESS_KEY")

    if not access_key or not secret_key:
        raise SystemExit(
            "SPACES_ACCESS_KEY/SPACES_SECRET_KEY or AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY must be set."
        )

    ensure_mime_types()

    endpoint_url = f"https://{args.region}.digitaloceanspaces.com"
    session = boto3.session.Session()
    client = session.client(
        "s3",
        region_name=args.region,
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )

    prefix = args.prefix.strip("/")
    files = iter_asset_files(dist)

    if not files:
        raise SystemExit(f"No asset files found in: {dist}")

    uploaded: list[str] = []
    failed: list[tuple[str, str]] = []

    for path in files:
        rel_path = path.relative_to(dist).as_posix()
        key = f"{prefix}/{rel_path}" if prefix else rel_path
        content_type, _ = mimetypes.guess_type(path.name)
        extra_args = {
            "CacheControl": args.cache_control,
            "ACL": args.acl,
        }
        if content_type:
            extra_args["ContentType"] = content_type

        if args.dry_run:
            print(f"[dry-run] {path} -> s3://{args.space}/{key}")
            uploaded.append(key)
            continue

        try:
            client.upload_file(str(path), args.space, key, ExtraArgs=extra_args)
            uploaded.append(key)
            print(f"Uploaded: s3://{args.space}/{key}")
        except Exception as e:
            failed.append((key, str(e)))
            print(f"FAILED: s3://{args.space}/{key} - {e}")

    # Print summary
    print(f"\n{'=' * 40}")
    print(f"Upload Summary: {len(uploaded)}/{len(files)} files")
    if prefix:
        print(f"Location: s3://{args.space}/{prefix}/")
    if failed:
        print(f"\nFailed uploads ({len(failed)}):")
        for key, err in failed:
            print(f"  - {key}: {err}")
        raise SystemExit(1)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
