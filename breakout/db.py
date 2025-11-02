from supabase import create_client, Client
from typing import List, Dict, Optional
from .settings import SUPABASE_URL, SUPABASE_KEY
import logging

logger = logging.getLogger(__name__)

def get_supabase_client() -> Optional[Client]:
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.warning("Supabase credentials are not set in environment.")
        return None
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        logger.exception("Failed to create Supabase client: %s", e)
        return None

def insert_failures(records):
    client = get_supabase_client()
    if not client:
        print("Supabase client not initialized.")
        return {"data": None, "error": "Client not initialized"}
    
    try:
        res = client.table("breakout_failures").insert(records).execute()
        return {"data": res.data, "error": None}
    except Exception as e:
        print(f"Error inserting records into supabase: {e}")
        return {"data": None, "error": str(e)}
