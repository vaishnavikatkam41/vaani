# Tests must never call a real AI service, even if a key is set in your terminal
# or in the private .env file.
import os

os.environ["VAANI_SKIP_ENV_FILE"] = "1"
for _name in ("SARVAM_API_KEY", "VAANI_ADMIN_TOKEN"):
    os.environ.pop(_name, None)
