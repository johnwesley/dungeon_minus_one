import asyncio
import logging
from datetime import datetime, timezone
import httpx
from app.config import get_settings
from app.metrics import BILLING_DO_COST_MTD, BILLING_CLAUDE_COST_MTD

logger = logging.getLogger(__name__)

class BillingService:
    def __init__(self):
        self.settings = get_settings()
        self._running = False
        self._task = None

    async def start(self):
        """Start the background billing sync task."""
        if self._running:
            return
        
        # Only start if at least one token is configured
        if not self.settings.digitalocean_token and not self.settings.anthropic_admin_api_key:
            logger.warning("BillingService: No API keys configured. Cost monitoring disabled.")
            return

        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("BillingService started.")

    async def stop(self):
        """Stop the background task."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("BillingService stopped.")

    async def _loop(self):
        """Main sync loop running periodically."""
        # Initial sync immediately
        try:
            await self.sync_costs()
        except Exception as e:
            logger.error(f"BillingService initial sync error: {e}")

        while self._running:
            # Sleep for 1 hour (3600 seconds)
            for _ in range(60): 
                if not self._running:
                    break
                await asyncio.sleep(60)
            
            if self._running:
                try:
                    await self.sync_costs()
                except Exception as e:
                    logger.error(f"BillingService loop error: {e}", exc_info=True)

    async def sync_costs(self):
        """Fetch and update cost metrics."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            tasks = []
            if self.settings.digitalocean_token:
                tasks.append(self._sync_do_costs(client))
            if self.settings.anthropic_admin_api_key:
                tasks.append(self._sync_claude_costs(client))
            
            if tasks:
                await asyncio.gather(*tasks)

    async def _sync_do_costs(self, client: httpx.AsyncClient):
        try:
            url = "https://api.digitalocean.com/v2/customers/my/balance"
            headers = {
                "Authorization": f"Bearer {self.settings.digitalocean_token}",
                "Content-Type": "application/json"
            }
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            # "month_to_date_balance" is usually a string like "12.34"
            mtd_balance = float(data.get("month_to_date_balance", 0.0))
            BILLING_DO_COST_MTD.set(mtd_balance)
            logger.info(f"BillingService: Updated DO cost to ${mtd_balance}")

        except Exception as e:
            logger.error(f"Failed to sync DigitalOcean costs: {e}")

    async def _sync_claude_costs(self, client: httpx.AsyncClient):
        try:
            url = "https://api.anthropic.com/v1/organizations/cost_report"
            headers = {
                "x-api-key": self.settings.anthropic_admin_api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            }
            
            # Request costs for the current month
            now = datetime.now(timezone.utc)
            start_date = now.replace(day=1, hour=0, minute=0, second=0).strftime("%Y-%m-%d")
            # For end_date, we use today (API should return data up to yesterday or today)
            end_date = now.strftime("%Y-%m-%d")
            
            params = {
                "start_at": start_date,
                "end_at": end_date
            }
            
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Aggregating costs from the response
            # Assuming 'data' contains list of line items with 'amount_cents'
            total_cents = 0.0
            
            # Check if 'data' is the list or if it's nested
            items = data if isinstance(data, list) else data.get("data", [])
            
            for item in items:
                # Look for common cost fields
                if "amount_cents" in item:
                    total_cents += float(item["amount_cents"])
                elif "cost_cents" in item:
                    total_cents += float(item["cost_cents"])
            
            total_dollars = total_cents / 100.0
            BILLING_CLAUDE_COST_MTD.set(total_dollars)
            logger.info(f"BillingService: Updated Claude cost to ${total_dollars}")

        except Exception as e:
            logger.error(f"Failed to sync Claude costs: {e}")
