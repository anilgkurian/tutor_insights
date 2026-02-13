
import httpx
from src.config import settings
from src.logger import error

class AccountService:
    def __init__(self):
        self.base_url = settings.ACCOUNT_SERVICE_URL

    async def get_plan_details(self, profile_id: str):
        """
        Fetches plan details (features, quotas) for a given profile_id.
        Returns None if not found or error.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/subscriptions/plan-details/{profile_id}",
                    timeout=5.0
                )
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    return None
                else:
                    error(f"Failed to fetch plan details for {profile_id}: {response.text}")
                    return None
        except Exception as e:
            error(f"Error connecting to account service: {e}")
            return None

account_service = AccountService()
