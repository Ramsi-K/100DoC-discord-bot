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
   - `!linkrepo <repo_url>` - Link a public GitHub repo to your profile
   - `!github [n]` - DM yourself the last n commits from your linked repo (default 3)"
   - Admins: see below

## Admin Commands

- `!reset @user` — Reset a user's streak
- `!force-add @user day` — Set a user's day
- `!userstatus @user` — Check any user's streak
- `!list-users` — List all tracked users
- `!drop-user @user` — Remove a user from tracking
- `!inactive [days]` — List users inactive for N days (default 3)

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
   pip install discord.py python-dotenv
   ```

3. **Create a `.env` file:**

   ```env
   DISCORD_BOT_TOKEN=your-bot-token-here
   ```

4. **Run the bot:**

   ```bash
   python main.py
   ```

5. **Set up your Discord server:**
   - Create a `#100-days-log` channel.
   - Give the bot permissions to read/send messages, add reactions, and manage messages in relevant channels.

## Database

- Uses SQLite (`streaks.db`) for persistent tracking.
- Hall of Fame is stored in a separate table and shown via `!halloffame`.

## Contributing

Pull requests and suggestions are welcome!

## License

MIT
