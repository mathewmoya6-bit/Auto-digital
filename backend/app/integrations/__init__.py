# app/integrations/__init__.py
# Auto-D Kenya - Integrations Package
# ================================================================

"""External integrations for Auto-D Kenya."""

from .supabase import SupabaseClient
from .daraja import DarajaClient
from .resend import ResendClient

__all__ = [
    "SupabaseClient",
    "DarajaClient",
    "ResendClient"
]
