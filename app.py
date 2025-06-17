import modal
import os
import asyncio
import tempfile
import pathlib
import shutil

app = modal.App("discord-100doc-bot")
cpu_request = 0.125
cpu_limit = 1.0

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
    # Reload the volume to ensure we have the latest data
    try:
        db_volume.reload()
        print("Database volume loaded successfully")
    except Exception as e:
        print(f"Warning: Failed to reload database volume: {e}")
        print("Continuing with local database")
    
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
    db_path = "/data/streaks.db"
    # Only initialize if the database doesn't exist
    if not os.path.exists(db_path):
        from bot.database import DatabaseManager
        db = DatabaseManager(db_path)
        db.init_database()
        try:
            db_volume.commit()  # Commit changes to the volume
            print("Database changes committed to volume")
        except Exception as e:
            print(f"Warning: Failed to commit database to volume: {e}")
            print("Database will operate in local mode")
        return "Database initialized at /data/streaks.db"
    else:
        return "Database already exists at /data/streaks.db"


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

    try:
        logs_volume.reload()
    except Exception as e:
        print(f"Warning: Failed to reload logs volume: {e}")
    
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

    try:
        logs_volume.commit()
        print("Resource log committed to volume.")
    except Exception as e:
        print(f"Warning: Failed to commit logs to volume: {e}")
    
    return metrics


@app.local_entrypoint()
def main():
    print("Checking database...")
    result = init_db.remote()
    print(result)
    print("Starting Discord bot...")
    run_bot.remote()
    print("Bot is running. Monitoring resource usage...")
    log_resource_usage.remote()
