# 🤖 Meeting-to-Action Bot for Student Teams

An AI-powered Telegram bot that transforms meeting discussions into structured summaries, actionable tasks, and team follow-ups using Google Gemini and Google Sheets.

## ✨ Features

- **AI Meeting Analysis:** Uses Google Gemini to analyze meeting transcripts.
- **Meeting Summaries:** Generates concise meeting summaries and key decisions.
- **Task Extraction:** Extracts actionable tasks, owners, and deadlines.
- **Google Sheets Integration:** Stores meeting information and tasks in Google Sheets.
- **Task Management:** View tasks and update their status.
- **Task Tracking:** Check pending, completed, upcoming, and overdue tasks.
- **Duplicate Meeting Detection:** Helps prevent repeated processing of the same transcript.
- **Telegram Interface:** Interact with the bot through simple Telegram commands.
- **Reminders:** Supports deadline-related reminders.

## 🛠️ Tech Stack

- Python
- Telegram Bot API
- Google Gemini API
- Google Sheets API
- `python-telegram-bot`
- `google-genai`
- `gspread`
- `python-dotenv`

## 💬 Telegram Bot Commands

| Command | Description |
|---|---|
| `/start` | Start the bot |
| `/help` | Display help information |
| `/tasks` | View tasks |
| `/status` | Update a task's status |
| `/pending` | View pending tasks |
| `/completed` | View completed tasks |
| `/upcoming` | View upcoming tasks |
| `/overdue` | View overdue tasks |

## 🏗️ Project Structure

```text
Agentic-Ai/
│
├── bot.py                 # Telegram bot and command handlers
├── ai_agent.py            # Gemini AI meeting analysis
├── sheets.py              # Google Sheets integration
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (not committed)
├── service_account.json   # Google service account credentials (not committed)
└── README.md              # Project documentation
```

## ⚙️ Setup and Installation

### 1. Clone the repository

```bash
git clone https://github.com/Chrn08s/Agentic-Ai.git
cd Agentic-Ai
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_GROUP_CHAT_ID=your_telegram_group_chat_id
GEMINI_API_KEY=your_gemini_api_key
GOOGLE_SHEET_ID=your_google_sheet_id
TIMEZONE=Asia/Kolkata
REMINDER_TEST_INTERVAL=2
```

Never commit your actual API keys, bot token, or credentials to GitHub.

### 5. Configure Google Sheets

1. Create a Google Cloud project.
2. Enable the Google Sheets API.
3. Create a service account and download its JSON credentials.
4. Place the credentials file in the project directory.
5. Share your Google Sheet with the service account email address.
6. Configure the credentials file path as required by the project.

### 6. Run the bot

```bash
python bot.py
```

## 🔄 How It Works

1. A user sends meeting information to the Telegram bot.
2. The bot checks whether the meeting was already processed.
3. Google Gemini analyzes the meeting transcript.
4. The AI generates a summary, decisions, recommendations, and tasks.
5. Extracted meeting details and tasks are stored in Google Sheets.
6. Team members can track and update task statuses through Telegram.

## 📊 Google Sheets Integration

The project uses Google Sheets to maintain meeting records and task information, making it easier for student teams to track responsibilities and progress.

## 🔐 Security

- API keys and tokens are stored in environment variables.
- Service account credentials are kept outside version control.
- `.env`, `.venv/`, and `service_account.json` should remain excluded through `.gitignore`.

## 🚀 Future Improvements

- Web-based team dashboard
- Individual task assignments
- Automated daily reminders
- Weekly productivity reports
- Multi-team support

## 👨‍💻 Author

**Sagnik**

GitHub: [Chrn08s](https://github.com/Chrn08s)

---

*Built to help student teams turn meetings into meaningful action.*

## Hybrid AI Architecture

This project uses a hybrid AI system to analyze meeting transcripts and extract actionable tasks.

### AI Models

**Primary Model: Google Gemma 4 E2B (Local)**
- Runs locally using Ollama.
- No Gemini API usage for successful local requests.
- Extracts meeting summaries, decisions, recommendations, tasks, owners, and deadlines.

**Fallback Model: Gemini 3.5 Flash-Lite**
- Used when the local Gemma model fails.
- Requires a valid Gemini API key.
- Subject to Google AI API quotas and availability.

### Architecture

Telegram User
    |
    v
Telegram Bot
    |
    v
Local Gemma via Ollama
    |
    | If local AI fails
    v
Gemini API Fallback
    |
    v
Meeting Analysis
    |
    v
Google Sheets
    |
    v
Telegram Report

### Local AI Setup (macOS)

1. Install Ollama:
   https://ollama.com/download

2. Download the model:

   ```bash
   ollama pull gemma4:e2b
   ```

3. Install the Python package:

   ```bash
   pip install ollama
   ```

4. Start Ollama and verify the model:

   ```bash
   ollama run gemma4:e2b
   ```

### Run the Telegram Bot

Activate your Python virtual environment:

```bash
source .venv/bin/activate
```

Start the bot:

```bash
python bot.py
```

Keep Ollama running while the bot is active.

### Hybrid AI Behaviour

- Local Gemma is tried first.
- Gemini is called if local processing fails.
- If both models fail, the meeting is not saved as successfully processed.
- Gemini fallback may be affected by API quotas, service availability, and network errors.

### Important Requirements

- Python 3.11
- Ollama
- Gemma 4 E2B model
- Telegram Bot API credentials
- Google Sheets API credentials
- Gemini API key for fallback

### Deployment Note

The bot currently runs on the developer's MacBook.

For continuous availability:
- Keep the MacBook powered on.
- Maintain an internet connection.
- Keep Ollama running.
- Keep the Telegram bot process running.

Local AI processing requires the computer hosting Ollama to remain available.
