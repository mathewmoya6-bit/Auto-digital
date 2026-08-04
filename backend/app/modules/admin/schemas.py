# In router.py, update the get_user_services function

@router.get("/users/{user_id}/services", response_model=UserServicesResponse)
async def get_user_services(
    user_id: UUID,
    service: AdminService = Depends(get_admin_service),
):
    """Get all services purchased by a user."""
    try:
        user = await service.get_user_by_id(str(user_id))
        
        services = []
        for s in user.get("services", []):
            service_data = s.get("services", {})
            services.append(UserServiceItem(
                id=UUID(s["id"]),
                user_id=UUID(s["user_id"]),
                service_id=UUID(s["service_id"]),
                service_name=service_data.get("name"),
                service_code=ServiceCode(service_data["code"]) if service_data.get("code") else None,
                service_price=service_data.get("price"),
                status=UserServiceStatus(s.get("status", "active")),
                created_at=datetime.fromisoformat(s["created_at"]) if isinstance(s["created_at"], str) else s["created_at"],
                updated_at=datetime.fromisoformat(s["updated_at"]) if isinstance(s["updated_at"], str) else s["updated_at"],
            ))
        
        return UserServicesResponse(
            user_id=user_id,
            services=services,
            total=len(services),
        )
    except Exception as e:
        logger.error(f"Error getting user services: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
