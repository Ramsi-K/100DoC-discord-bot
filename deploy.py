import modal

if __name__ == "__main__":
    print("Deploying 100 Days of Code Discord Bot to Modal...")

    # First, make sure the database is initialized
    print("Initializing database...")
    f = modal.Function.from_name("discord-100doc-bot", "run_bot")
    f.remote()

    # Deploy the bot
    print("Deploying bot (keep_warm=1)...")
    # app.deploy("discord-100doc-bot")
    print("Bot deployed successfully!")
    print("\nYou can monitor your app at: https://modal.com/apps")
