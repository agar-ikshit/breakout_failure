import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

DEFAULT_PERIOD = os.getenv("DEFAULT_PERIOD", "1d")
DEFAULT_INTERVAL = os.getenv("DEFAULT_INTERVAL", "5m")

K_FACTOR = float(os.getenv("K_FACTOR", "1.5"))
LOCAL_WINDOW = int(os.getenv("LOCAL_WINDOW", "5"))
