# Tests must never call a real AI service, even if a key is set in your terminal.
import os

for _name in ("SARVAM_API_KEY", "ANTHROPIC_API_KEY", "VAANI_ADMIN_TOKEN"):
    os.environ.pop(_name, None)
