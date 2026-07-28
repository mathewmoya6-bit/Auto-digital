class NotificationService:
    def send_notification(self, user_id, message, type="info"):
        return {"status": "sent", "message": message}
