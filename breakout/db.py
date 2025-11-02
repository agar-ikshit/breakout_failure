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

def insert_failures(records: List[Dict]) -> Dict:
    """
    Insert a list of failure dicts into the `breakout_failures` table.
    Each record should include: company, ticker, location, failure_time (as ISO str or datetime).
    """
    client = get_supabase_client()
    if client is None:
        return {"error": "supabase_not_configured"}

    try:
        # supabase-py uses .table('name').insert(...).execute()
        res = client.table("breakout_failures").insert(records).execute()
        return {"data": res.data, "status_code": res.status_code}
    except Exception as e:
        logger.exception("Error inserting records into supabase: %s", e)
        return {"error": str(e)}
