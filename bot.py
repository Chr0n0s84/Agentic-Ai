import os
import asyncio

from dotenv import load_dotenv

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

from ai_agent import analyze_meeting

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


async def start(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    del _context


    welcome = """
🤖 Welcome to Meeting-to-Action Bot!

I am your AI Meeting Assistant.

Send me your meeting transcript.

I will automatically generate:

✅ Meeting Summary
✅ Key Decisions
✅ Action Items
✅ Task Owners
✅ Deadlines
✅ Missing Information

Let's make meetings productive!
"""

    if update.message is None:
        return

    await update.message.reply_text(welcome)


async def handle_message(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    del _context

    message = update.message
    if message is None or message.text is None:
        return

    transcript = message.text

    if len(transcript) > 12000:
        await message.reply_text(
            "Please send a shorter transcript (maximum 12,000 characters)."
        )
        return

    await message.reply_text(
        "🧠 AI is analyzing your meeting. Please wait..."
    )

    try:
        result = await asyncio.to_thread(
            analyze_meeting,
            transcript
        )

        if not result:
            result = "AI could not generate a response."

        # Telegram message limit
        for i in range(0, len(result), 4000):
            await message.reply_text(
                result[i:i + 4000]
            )

    except Exception as e:
        print("ERROR:", str(e))

        await message.reply_text(
            "❌ Something went wrong. Please check your API configuration."
        )


def main():

    if not TOKEN:
        raise ValueError("Telegram token missing in .env")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    print("🤖 Meeting-to-Action Bot is running!")

    app.run_polling()


if __name__ == "__main__":
    main()