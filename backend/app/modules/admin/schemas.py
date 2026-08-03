# ─── PAGINATED RESPONSE SCHEMAS ──────────────────────────────────

class AdminUsersResponse(Pagination):
    """Admin users response."""
    users: List[AdminUser] = Field(
        ...,
        description="List of users",
    )


class AdminPaymentsResponse(Pagination):
    """Admin payments response."""
    payments: List[AdminPayment] = Field(
        ...,
        description="List of payments",
    )


class AdminVehiclesResponse(Pagination):
    """Admin vehicles response."""
    vehicles: List[AdminVehicle] = Field(
        ...,
        description="List of vehicles",
    )
