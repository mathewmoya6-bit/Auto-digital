from app.core.database import get_supabase


class AdminService:
    def __init__(self):
        self.db = get_supabase()

    async def dashboard(self):
        return {
            "total_users": 0,
            "total_vehicles": 0,
            "total_payments": 0,
            "total_revenue": 0.0,
        }

    async def list_services(self):
        result = self.db.table("services").select("*").execute()
        return result.data or []

    async def update_service(self, service_id: int, data: dict):
        result = (
            self.db.table("services")
            .update(data)
            .eq("id", service_id)
            .execute()
        )

        return result.data
