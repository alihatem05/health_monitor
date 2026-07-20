from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
FLUSH_INTERVAL = int(os.getenv("FLUSH_INTERVAL", 5))