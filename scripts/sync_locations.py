import argparse
import asyncio
import json
import os
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import SQLAlchemyError

# Add project root to Python path
sys.path.append(os.getcwd())

from app.database import Base, async_session_factory, engine
from app.models.database import GameState, Location, LocationExit


@dataclass(frozen=True)
class FixtureLocation:
    id: str
    name: str
    description: str
    interactables: list[Any]
    npcs: list[Any]
    exits: dict[str, str]


def load_location_fixtures(locations_dir: Path) -> tuple[dict[str, FixtureLocation], dict[tuple[str, str], str]]:
    if not locations_dir.exists():
        raise FileNotFoundError(f"Locations dir not found: {locations_dir}")

    fixtures: dict[str, FixtureLocation] = {}
    exit_map: dict[tuple[str, str], str] = {}

    for file_path in sorted(locations_dir.glob("*.json")):
        if file_path.name == "__init__.json":
            continue

        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON: {file_path}") from exc

        loc_id = data.get("id") or file_path.stem
        if loc_id in fixtures:
            raise ValueError(f"Duplicate location id '{loc_id}' from {file_path}")

        exits = data.get("exits") or {}
        if not isinstance(exits, dict):
            raise ValueError(f"Invalid exits for '{loc_id}' in {file_path}: expected object/dict")

        fixture = FixtureLocation(
            id=loc_id,
            name=data.get("name", "Unknown"),
            description=data.get("description", ""),
            interactables=data.get("interactables", []) or [],
            npcs=data.get("npcs", []) or [],
            exits={str(direction): str(target_id) for direction, target_id in exits.items()},
        )
        fixtures[loc_id] = fixture

        for direction, target_id in fixture.exits.items():
            exit_map[(loc_id, direction)] = target_id

    return fixtures, exit_map


def validate_fixtures(
    fixtures: dict[str, FixtureLocation],
    exit_map: dict[tuple[str, str], str],
    *,
    prune: bool,
    reset_current_location_to: str,
) -> None:
    if not fixtures:
        raise ValueError("No location fixtures found.")

    fixture_ids = set(fixtures.keys())

    if prune and reset_current_location_to not in fixture_ids:
        raise ValueError(
            f"--reset-current-location-to '{reset_current_location_to}' is not present in fixtures; "
            "refusing to prune."
        )

    invalid_targets: list[tuple[str, str, str]] = []
    for (source_id, direction), target_id in exit_map.items():
        if target_id not in fixture_ids:
            invalid_targets.append((source_id, direction, target_id))

    if invalid_targets:
        rendered = ", ".join(
            f"{source}.{direction}->{target}" for source, direction, target in invalid_targets[:10]
        )
        suffix = "" if len(invalid_targets) <= 10 else f" (+{len(invalid_targets) - 10} more)"
        raise ValueError(f"Invalid exits (missing target ids) in fixtures: {rendered}{suffix}")

async def verify_db_matches_fixtures(
    *,
    fixture_ids: set[str],
    fixtures: dict[str, FixtureLocation],
    exit_map: dict[tuple[str, str], str],
    prune: bool,
    reset_current_location_to: str,
) -> None:
    problems: list[str] = []

    async with async_session_factory() as session:
        # Locations presence / exactness
        db_locations = (await session.execute(select(Location))).scalars().all()
        db_location_ids = {loc.id for loc in db_locations}
        missing_locations = sorted(fixture_ids - db_location_ids)
        if missing_locations:
            problems.append(f"Missing locations in DB: {missing_locations[:20]}" + (" ..." if len(missing_locations) > 20 else ""))

        if prune:
            extra_locations = sorted(db_location_ids - fixture_ids)
            if extra_locations:
                problems.append(f"Extra locations in DB (not in fixtures): {extra_locations[:20]}" + (" ..." if len(extra_locations) > 20 else ""))

        # Location field equality (fixtures are source of truth)
        db_locations_by_id = {loc.id: loc for loc in db_locations if loc.id in fixture_ids}
        location_mismatches: list[str] = []
        for loc_id, fixture in fixtures.items():
            db_loc = db_locations_by_id.get(loc_id)
            if not db_loc:
                continue
            if db_loc.name != fixture.name:
                location_mismatches.append(f"{loc_id}.name")
            if db_loc.description != fixture.description:
                location_mismatches.append(f"{loc_id}.description")
            if (db_loc.interactables or []) != fixture.interactables:
                location_mismatches.append(f"{loc_id}.interactables")
            if (db_loc.npcs or []) != fixture.npcs:
                location_mismatches.append(f"{loc_id}.npcs")
        if location_mismatches:
            problems.append(
                "Location field mismatches: "
                + ", ".join(location_mismatches[:20])
                + (" ..." if len(location_mismatches) > 20 else "")
            )

        # Uniqueness: one exit per (source_id, direction)
        dup_rows = (
            await session.execute(
                select(LocationExit.source_id, LocationExit.direction, func.count())
                .group_by(LocationExit.source_id, LocationExit.direction)
                .having(func.count() > 1)
            )
        ).all()
        if dup_rows:
            sample = ", ".join(f"{s}.{d} (x{c})" for s, d, c in dup_rows[:20])
            problems.append(f"Duplicate exits for (source,direction): {sample}" + (" ..." if len(dup_rows) > 20 else ""))

        # Orphaned exits (source/target must exist as locations)
        orphan_count = (
            await session.execute(
                select(func.count())
                .select_from(LocationExit)
                .where(
                    (~LocationExit.source_id.in_(select(Location.id).scalar_subquery()))
                    | (~LocationExit.target_id.in_(select(Location.id).scalar_subquery()))
                )
            )
        ).scalar_one()
        if orphan_count and orphan_count > 0:
            problems.append(f"Orphaned exits (missing source/target location): {orphan_count}")

        # Fixture-defined exits exist and match target_id
        fixture_sources = {source_id for (source_id, _direction) in exit_map.keys()}
        db_exits = (
            await session.execute(
                select(LocationExit.source_id, LocationExit.direction, LocationExit.target_id)
                .where(LocationExit.source_id.in_(fixture_sources))
            )
        ).all()
        db_exit_map: dict[tuple[str, str], str] = {(s, d): t for s, d, t in db_exits}

        missing_exit_keys = sorted(set(exit_map.keys()) - set(db_exit_map.keys()))
        if missing_exit_keys:
            sample = ", ".join(f"{s}.{d}" for s, d in missing_exit_keys[:20])
            problems.append(f"Missing exits in DB: {sample}" + (" ..." if len(missing_exit_keys) > 20 else ""))

        mismatched: list[str] = []
        for key, expected_target in exit_map.items():
            actual_target = db_exit_map.get(key)
            if actual_target is None:
                continue
            if actual_target != expected_target:
                mismatched.append(f"{key[0]}.{key[1]}: db={actual_target} fixture={expected_target}")
        if mismatched:
            problems.append("Exit target mismatches: " + "; ".join(mismatched[:10]) + (" ..." if len(mismatched) > 10 else ""))

        if prune:
            # After prune we should not have any game states pointing to missing locations
            dangling_state_count = (
                await session.execute(
                    select(func.count()).select_from(GameState).where(
                        ~GameState.current_location.in_(select(Location.id).scalar_subquery())
                    )
                )
            ).scalar_one()
            if dangling_state_count and dangling_state_count > 0:
                problems.append(
                    f"Game states still pointing to missing locations: {dangling_state_count} (expected 0 after reset to '{reset_current_location_to}')"
                )

        if problems:
            rendered = "\n- ".join(problems)
            raise RuntimeError(f"Location fixture verification failed:\n- {rendered}")


async def sync_locations(
    *,
    locations_dir: Path,
    prune: bool,
    reset_current_location_to: str,
    verify: bool,
    dry_run: bool,
) -> None:
    fixtures, exit_map = load_location_fixtures(locations_dir)
    validate_fixtures(
        fixtures,
        exit_map,
        prune=prune,
        reset_current_location_to=reset_current_location_to,
    )

    fixture_ids = set(fixtures.keys())

    if dry_run:
        print("Dry-run: verifying DB matches fixtures (no writes)...")
        await verify_db_matches_fixtures(
            fixture_ids=fixture_ids,
            fixtures=fixtures,
            exit_map=exit_map,
            prune=prune,
            reset_current_location_to=reset_current_location_to,
        )
        print("Dry-run verification passed.")
        return

    async with async_session_factory() as session:
        print("Ensuring tables exist...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        print(f"Syncing {len(fixtures)} locations from JSON...")

        with session.no_autoflush:
            for fixture in fixtures.values():
                existing = await session.get(Location, fixture.id)
                if existing:
                    existing.name = fixture.name
                    existing.description = fixture.description
                    existing.interactables = fixture.interactables
                    existing.npcs = fixture.npcs
                else:
                    session.add(
                        Location(
                            id=fixture.id,
                            name=fixture.name,
                            description=fixture.description,
                            interactables=fixture.interactables,
                            npcs=fixture.npcs,
                        )
                    )

        await session.flush()

        if prune:
            print("Pruning missing locations/exits and repairing game state...")

            await session.execute(
                update(GameState)
                .where(~GameState.current_location.in_(fixture_ids))
                .values(current_location=reset_current_location_to)
            )

            await session.execute(
                delete(LocationExit).where(
                    (~LocationExit.source_id.in_(fixture_ids))
                    | (~LocationExit.target_id.in_(fixture_ids))
                )
            )

            await session.execute(delete(Location).where(~Location.id.in_(fixture_ids)))
            await session.flush()

        print("Reconciling exits (unique per source+direction)...")
        result = await session.execute(select(LocationExit).where(LocationExit.source_id.in_(fixture_ids)))
        existing_exits = list(result.scalars().all())

        exits_by_key: dict[tuple[str, str], list[LocationExit]] = defaultdict(list)
        for exit_row in existing_exits:
            exits_by_key[(exit_row.source_id, exit_row.direction)].append(exit_row)

        fixture_keys = set(exit_map.keys())

        for (source_id, direction), target_id in exit_map.items():
            if target_id not in fixture_ids:
                print(
                    f"Warning: Target location '{target_id}' not found for exit "
                    f"from '{source_id}' direction '{direction}'. Skipping."
                )
                continue

            rows = exits_by_key.get((source_id, direction), [])
            if not rows:
                session.add(
                    LocationExit(source_id=source_id, target_id=target_id, direction=direction)
                )
                continue

            keep = rows[0]
            if keep.target_id != target_id:
                keep.target_id = target_id

            for extra in rows[1:]:
                await session.delete(extra)

        if prune:
            for (source_id, direction), rows in exits_by_key.items():
                if (source_id, direction) not in fixture_keys:
                    for row in rows:
                        await session.delete(row)

        await session.commit()
        print("Location sync complete.")

    if verify:
        print("Verifying DB matches fixtures...")
        await verify_db_matches_fixtures(
            fixture_ids=fixture_ids,
            fixtures=fixtures,
            exit_map=exit_map,
            prune=prune,
            reset_current_location_to=reset_current_location_to,
        )
        print("Verification passed.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Sync static location fixtures (data/locations/*.json) into the database.",
    )
    parser.add_argument(
        "--locations-dir",
        default="data/locations",
        help="Directory containing location fixture JSON files (default: data/locations).",
    )
    parser.add_argument(
        "--prune",
        action="store_true",
        help="Delete locations/exits not present in fixtures and reset invalid game states.",
    )
    parser.add_argument(
        "--reset-current-location-to",
        default="start",
        help="When pruning, move game states whose current_location is missing to this location id (default: start).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not write anything; only verify whether the DB matches the fixtures (exit non-zero on mismatch).",
    )
    verify_group = parser.add_mutually_exclusive_group()
    verify_group.add_argument(
        "--verify",
        action="store_true",
        default=True,
        help="Verify DB consistency with fixtures after syncing (default).",
    )
    verify_group.add_argument(
        "--no-verify",
        action="store_true",
        help="Skip verification after syncing.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    try:
        asyncio.run(
            sync_locations(
                locations_dir=Path(args.locations_dir),
                prune=bool(args.prune),
                reset_current_location_to=str(args.reset_current_location_to),
                verify=bool(args.verify) and (not bool(args.no_verify)),
                dry_run=bool(args.dry_run),
            )
        )
    except (ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from None
    except SQLAlchemyError as exc:
        print(f"Database error: {exc}", file=sys.stderr)
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
