from functools import lru_cache

from supabase import Client, create_client

from app.config import settings


@lru_cache
def get_supabase_client() -> Client:
    """Create and cache the Supabase client."""

    return create_client(
        settings.supabase_url,
        settings.supabase_publishable_key,
    )


supabase: Client = get_supabase_client()