import modal
import os
import asyncio
import tempfile
import pathlib
import shutil

app = modal.App("discord-100doc-bot")
cpu_request = 1.0
cpu_limit = 4.0

# Remote, persisted volumes
db_volume = modal.Volume.from_name("discord-bot-db", create_if_missing=True)
logs_volume = modal.Volume.from_name(
    "discord-bot-logs", create_if_missing=True
)

image = (
    modal.Image.debian_slim()
    .run_commands("pip install --upgrade pip")
    .run_commands("pip install --upgrade setuptools")
    .pip_install_from_requirements("requirements.txt")
    .pip_install("psutil")
    .add_local_dir(local_path="bot", remote_path="/root/bot", copy=True)
)

LOGS_DIR = "/logs"
LOGS_FILENAME = "resource_metrics.json"
LOGS_PATH = pathlib.Path(LOGS_DIR) / LOGS_FILENAME


@app.function(
    image=image,
    volumes={"/data": db_volume},
    # keep_warm=1,
    cpu=(cpu_request, cpu_limit),
    secrets=[modal.Secret.from_name("discord-secret")],
    timeout=60 * 60 * 24,  # 24 hours
)
def run_bot():
    os.makedirs("/data", exist_ok=True)
    os.environ["DB_PATH"] = "/data/streaks.db"
    os.environ["DISCORD_BOT_TOKEN"] = os.environ["DISCORD_BOT_TOKEN"]

    from bot.bot_core import HundredDoCBot
    from bot.commands.general import GeneralCommands
    from bot.commands.admin import AdminCommands

    async def main():
        bot = HundredDoCBot()
        await bot.add_cog(GeneralCommands(bot))
        await bot.add_cog(AdminCommands(bot))
        await bot.start(os.environ["DISCORD_BOT_TOKEN"])

    asyncio.run(main())


@app.function(
    image=image,
    volumes={"/data": db_volume},
)
def init_db():
    os.makedirs("/data", exist_ok=True)
    from bot.database import DatabaseManager

    db = DatabaseManager("/data/streaks.db")
    db.init_database()
    return "Database initialized at /data/streaks.db"


@app.function(
    image=image,
    schedule=modal.Period(hours=1),
    volumes={LOGS_DIR: logs_volume},
    timeout=900,
)
def log_resource_usage():
    import psutil
    import json
    from datetime import datetime

    logs_volume.reload()
    os.makedirs(LOGS_DIR, exist_ok=True)

    metrics = {
        "timestamp": datetime.now().isoformat(),
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory_mb": psutil.Process().memory_info().rss / (1024 * 1024),
        "threads": len(psutil.Process().threads()),
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_logs_path = pathlib.Path(tmpdir) / LOGS_FILENAME
        # Copy existing logs if present
        if LOGS_PATH.exists():
            shutil.copyfile(LOGS_PATH, tmp_logs_path)
        # Append new metrics
        with open(tmp_logs_path, "a") as f:
            f.write(json.dumps(metrics) + "\n")
        # Ensure logs dir exists and copy back
        pathlib.Path(LOGS_DIR).mkdir(parents=True, exist_ok=True)
        shutil.copyfile(tmp_logs_path, LOGS_PATH)

    logs_volume.commit()
    print("Resource log committed to volume.")
    return metrics


@app.local_entrypoint()
def main():
    print("Initializing database...")
    init_db.remote()
    print("Starting Discord bot...")
    run_bot.remote()
    print("Bot is running. Monitoring resource usage...")
    log_resource_usage.remote()
