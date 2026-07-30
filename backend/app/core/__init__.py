# backend/app/core/__init__.py

from .config import settings
from .database import get_supabase

from .security import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)

from .dependencies import (
    get_current_user,
    get_current_user_optional,
)

from .exceptions import (
    AppException,
    NotFoundException,
    UnauthorizedException,
    ForbiddenException,
    ValidationException,
)

__all__ = [
    "settings",
    "get_supabase",
    "create_access_token",
    "decode_token",
    "hash_password",
    "verify_password",
    "get_current_user",
    "get_current_user_optional",
    "AppException",
    "NotFoundException",
    "UnauthorizedException",
    "ForbiddenException",
    "ValidationException",
]


2. backend/app/scrapers/__init__.py

Replace with:

# backend/app/scrapers/__init__.py

from .base_scraper import BaseScraper
from .jiji import JijiScraper
from .cheki import ChekiScraper
from .autochek import AutochekScraper
from .beepbeep import BeepBeepScraper

__all__ = [
    "BaseScraper",
    "JijiScraper",
    "ChekiScraper",
    "AutochekScraper",
    "BeepBeepScraper",
]
