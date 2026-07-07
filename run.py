import subprocess
import sys
import os

port = os.environ.get("PORT", "5000")
sklepp_dir = os.path.join(os.path.dirname(__file__), "sklepp_bot")

# Start web server
web = subprocess.Popen(
    [sys.executable, "web.py"],
    cwd=sklepp_dir,
    env={**os.environ, "PORT": port}
)

# Start bot
bot = subprocess.Popen(
    [sys.executable, "bot.py"],
    cwd=sklepp_dir
)

try:
    web.wait()
    bot.wait()
except KeyboardInterrupt:
    web.terminate()
    bot.terminate()
