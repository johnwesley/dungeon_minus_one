import argparse
import asyncio
import os
import sys
from datetime import datetime

# Add project root to Python path
sys.path.append(os.getcwd())

from app.config import get_settings
from app.database import async_session_factory, init_db
from app.services.email_service import EmailService
from app.services.invite_service import InviteService


async def generate_invite(email: str, never_expires: bool, send_email: bool) -> None:
    # Ensure tables exist (dev/local)
    await init_db()

    settings = get_settings()
    async with async_session_factory() as session:
        invite_service = InviteService(session, settings)
        invite, token = await invite_service.create_invite(email, never_expires)

        if send_email and settings.invite_email_send_mode == "auto":
            email_service = EmailService()
            await email_service.send_invite_email(invite.invite_email, token)
            invite.sent_at = datetime.utcnow()
            await session.commit()
            print(f"Invite email sent to {invite.invite_email} (invite_id={invite.id}).")
            return

        await session.commit()
        print(f"Invite token generated for {invite.invite_email}: {token}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate an invite token bound to an email.")
    parser.add_argument("email", help="Email address to bind the invite")
    parser.add_argument("--never-expires", action="store_true", help="Create an invite without expiry")
    parser.add_argument("--send-email", action="store_true", help="Send invite via Postmark (auto mode only)")
    args = parser.parse_args()

    asyncio.run(generate_invite(args.email, args.never_expires, args.send_email))
