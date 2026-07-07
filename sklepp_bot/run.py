import subprocess
import sys
import os

port = os.environ.get("PORT", "5000")

# Start web server
web = subprocess.Popen([sys.executable, "web.py"], env={**os.environ, "PORT": port})

# Start bot
bot = subprocess.Popen([sys.executable, "bot.py"])

try:
    web.wait()
    bot.wait()
except KeyboardInterrupt:
    web.terminate()
    bot.terminate()
