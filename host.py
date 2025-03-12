import os
import subprocess
import logging
import asyncio
from pyrogram import Client, filters

# Logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Replace with your API credentials
API_ID = os.getenv("API_ID", 7249983)
API_HASH = os.getenv("API_HASH", "be8ea36c220d5e879c91ad9731686642")
ADMIN_ID = os.getenv("ADMIN_ID", 7143123520)# Replace with your Telegram ID

# Directory where bots will be cloned and stored
BOTS_DIR = "deployed_bots"
os.makedirs(BOTS_DIR, exist_ok=True)

# Pyrogram bot to manage deployments
admin_bot = Client("bot_deployer", api_id=API_ID, api_hash=API_HASH)

# Dictionary to store running bot processes
bot_processes = {}

# Function to send logs to Telegram
async def send_log_to_admin(log_message):
    async with Client("log_notifier", api_id=API_ID, api_hash=API_HASH) as notifier:
        await notifier.send_message(ADMIN_ID, f"🚨 **Bot Error:**\n\n{log_message}")

# Function to deploy a bot from GitHub
@admin_bot.on_message(filters.command("deploy") & filters.user(ADMIN_ID))
async def deploy_bot(_, message):
    args = message.text.split()
    if len(args) < 3:
        await message.reply_text("❌ Usage: /deploy <bot_name> <github_repo_url>")
        return

    bot_name, repo_url = args[1], args[2]
    bot_path = os.path.join(BOTS_DIR, bot_name)

    try:
        if os.path.exists(bot_path):
            subprocess.run(["git", "-C", bot_path, "pull"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        else:
            subprocess.run(["git", "clone", repo_url, bot_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Start the bot
        process = subprocess.Popen(["python3", os.path.join(bot_path, "main.py")], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        bot_processes[bot_name] = process

        await message.reply_text(f"🚀 `{bot_name}` deployed and running!")

    except Exception as e:
        error_message = f"Failed to deploy `{bot_name}`:\n\n{str(e)}"
        await send_log_to_admin(error_message)

# Function to check running bots
@admin_bot.on_message(filters.command("status") & filters.user(ADMIN_ID))
async def status(_, message):
    running_bots = ", ".join(bot_processes.keys()) if bot_processes else "No bots running"
    await message.reply_text(f"🤖 **Running Bots:**\n{running_bots}")

# Function to stop a bot
@admin_bot.on_message(filters.command("stop") & filters.user(ADMIN_ID))
async def stop_bot(_, message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply_text("❌ Usage: /stop <bot_name>")
        return

    bot_name = args[1]
    if bot_name in bot_processes:
        bot_processes[bot_name].terminate()
        del bot_processes[bot_name]
        await message.reply_text(f"🛑 Stopped `{bot_name}`")
    else:
        await message.reply_text(f"❌ Bot `{bot_name}` not found!")

# Function to restart a bot
@admin_bot.on_message(filters.command("restart") & filters.user(ADMIN_ID))
async def restart_bot(_, message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply_text("❌ Usage: /restart <bot_name>")
        return

    bot_name = args[1]
    if bot_name in bot_processes:
        bot_processes[bot_name].terminate()

        bot_path = os.path.join(BOTS_DIR, bot_name)
        process = subprocess.Popen(["python3", os.path.join(bot_path, "main.py")], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        bot_processes[bot_name] = process

        await message.reply_text(f"🔄 Restarted `{bot_name}`")
    else:
        await message.reply_text(f"❌ Bot `{bot_name}` not found!")

# Function to monitor bot logs and detect errors
async def monitor_logs():
    while True:
        for bot_name, process in bot_processes.items():
            if process.poll() is not None:  # Check if bot crashed
                error_message = process.stderr.read().decode("utf-8")
                logging.error(f"Bot {bot_name} crashed: {error_message}")
                await send_log_to_admin(f"Bot `{bot_name}` crashed:\n\n```{error_message}```")

                # Restart bot
                bot_path = os.path.join(BOTS_DIR, bot_name)
                new_process = subprocess.Popen(["python3", os.path.join(bot_path, "main.py")], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                bot_processes[bot_name] = new_process

                await send_log_to_admin(f"🔄 Auto-restarted `{bot_name}`")

        await asyncio.sleep(5)  # Check logs every 5 seconds

# Run the admin bot
async def main():
    await admin_bot.start()
    logging.info("Admin bot started!")
    await asyncio.gather(monitor_logs())  # Start monitoring logs

asyncio.run(main())
                      
