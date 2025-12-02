import asyncio
import json
import sys
import os
from pathlib import Path
from sqlalchemy import select

# Add project root to Python path
sys.path.append(os.getcwd())

from app.database import async_session_factory, engine, Base
from app.models.database import Location, LocationExit

LOCATIONS_DIR = Path("data/locations")

async def seed_locations():
    async with async_session_factory() as session:
        print("Creating tables...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
        print("Loading locations from JSON...")
        locations_data = []
        exits_data = []
        
        # First pass: Create Location objects
        for file_path in LOCATIONS_DIR.glob("*.json"):
            if file_path.name == "__init__.json": 
                continue
            
            # Skip __init__.py/pyc if glob catches them (it shouldn't with *.json)
            
            try:
                data = json.loads(file_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                print(f"Skipping invalid JSON: {file_path}")
                continue
                
            loc_id = data.get("id") or file_path.stem
            
            loc = Location(
                id=loc_id,
                name=data.get("name", "Unknown"),
                description=data.get("description", ""),
                interactables=data.get("interactables", []),
                npcs=data.get("npcs", [])
            )
            locations_data.append(loc)
            
            # Collect exits for second pass
            for direction, target_id in data.get("exits", {}).items():
                exits_data.append({
                    "source_id": loc_id,
                    "target_id": target_id,
                    "direction": direction
                })
        
        print(f"Found {len(locations_data)} locations.")
        
        # Upsert Locations
        for loc in locations_data:
            existing = await session.get(Location, loc.id)
            if existing:
                existing.name = loc.name
                existing.description = loc.description
                existing.interactables = loc.interactables
                existing.npcs = loc.npcs
            else:
                session.add(loc)
        
        await session.flush()
        
        print("Processing exits...")
        location_ids = {l.id for l in locations_data}
        
        for exit_info in exits_data:
            if exit_info["target_id"] not in location_ids:
                print(f"Warning: Target location '{exit_info['target_id']}' not found for exit from '{exit_info['source_id']}'. Skipping.")
                continue
            
            # Check if exit exists
            result = await session.execute(
                select(LocationExit).where(
                    LocationExit.source_id == exit_info["source_id"],
                    LocationExit.target_id == exit_info["target_id"],
                    LocationExit.direction == exit_info["direction"]
                )
            )
            existing_exit = result.scalar_one_or_none()
            
            if not existing_exit:
                new_exit = LocationExit(
                    source_id=exit_info["source_id"],
                    target_id=exit_info["target_id"],
                    direction=exit_info["direction"]
                )
                session.add(new_exit)
        
        await session.commit()
        print("Migration complete.")

if __name__ == "__main__":
    asyncio.run(seed_locations())

