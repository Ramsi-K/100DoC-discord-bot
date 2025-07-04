# 100 Days of Cloud Discord Bot

A feature-rich Discord bot to help your community track, celebrate, and manage their 100 Days of Code challenge!

## Features

- **Daily Logging:** Users log progress with `[day/100]` in a dedicated channel.
- **Streak Tracking:** Tracks each user's current day, last post, and streak status.
- **Leaderboard:** `!leaderboard` shows the top 5 active streaks.
- **Status:** `!status` for users to check their own streak health.
- **Admin User Status:** `!userstatus @user` for admins to check any user's streak.
- **Reminders:** Automatic DMs and public reminders for inactivity (3, 5, 7, 14 days).
- **Opt-in/out:** `!remind-toggle` lets users control DM reminders.
- **GitHub Integration:**
  - `!linkrepo <repo_url>` — Link a public GitHub repo to your profile
  - `!github [n]` — DM yourself the last n commits from your linked repo
- **Admin Tools:**
  - `!reset @user` — Reset a user's streak
  - `!force-add @user day` — Set a user's day
  - `!list-users` — List all tracked users
  - `!drop-user @user` — Remove a user from tracking
  - `!inactive [days]` — List users inactive for N days
- **Hall of Fame:** `!hall-of-fame` shows users who completed 100 days.

## Usage

1. **Log your progress:**
   - Post in `#100-days-log` with `[day/100] Your message` (e.g. `[1/100] Started learning Python!`).
   - Only one log per day (UTC).
2. **Commands:**
   - `!leaderboard` — See top streaks
   - - `!help` — Show full list of available commands (auto-hides admin commands if you're not an admin)
   - `!status` — See your streak
   - `!myrank` — See your leaderboard rank
   - `!remind-toggle` — Opt in/out of inactivity DMs
   - `!hall-of-fame` — See the Hall of Fame
   - `!linkrepo <repo_url>` — Link a public GitHub repo to your profile
   - `!github [n]` — DM yourself the last n commits from your linked repo (default 3)"
   - Admins: see below

## Admin Commands

- `!reset @user` — Reset a user's streak
- `!force-add @user day` — Set a user's day
- `!userstatus @user` — Check any user's streak
- `!list-users` — List all tracked users
- `!drop-user @user` — Remove a user from tracking
- `!inactive [days]` — List users inactive for N days (default 3)

## Deploy on Modal

1. **Clone the repo:**

   ```bash
   git clone <your-repo-url>
   cd 100DoC-discord-bot
   ```

2. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Setup your Modal Account and setup modal the Discord Bot Token:**

   ```bash
   modal setup
   ```

4. **Save Discord Bot Token in Modal Secrets:**

   ```env
   discord-secret=DISCORD_BOT_TOKEN
   ```

5. **Deploy and Run the Modal App:**
   ```bash
   modal deploy app.py
   python deploy.py
   ```

This sets up the app to run on Modal. Closing the terminal or ctrl+C will not stop the app. To stop the app, go to the Modal dashboard.

## Setup

1. **Clone the repo:**

   ```bash
   git clone <your-repo-url>
   cd 100DoC-discord-bot
   ```

2. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   # or
   pip install discord.py python-dotenv aiohttp
   ```

3. **Create a `.env` file:**

   ```env
   DISCORD_BOT_TOKEN=your-bot-token-here
   ```

### Docker (Recommended)

1. **Build and run with Docker Compose:**
   ```bash
   docker-compose up --build -d
   ```
2. **Your SQLite DB will be stored in `./data/streaks.db` and will persist across restarts.**
3. **The bot will restart automatically on crash or reboot.**

- If running on Windows, use Docker Desktop and run the above commands in PowerShell or CMD.

## Database

- Uses SQLite (`streaks.db`) for persistent tracking.
- All tables (`user_streaks`, `hall_of_fame`, `user_repos`) are auto-initialized.
- Hall of Fame is stored in a separate table and shown via `!halloffame`.

## Contributing

Pull requests and suggestions are welcome!

## License

MIT
