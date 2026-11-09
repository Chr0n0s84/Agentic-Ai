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

from ai_agent import analyze_meeting_once
from sheets import save_meeting, meeting_exists

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
        # Check duplicate BEFORE using Gemini API
        already_exists = await asyncio.to_thread(
            meeting_exists,
            transcript
        )

        if already_exists:
            await message.reply_text(
                "⚠️ This meeting has already been saved. "
                "No duplicate records were added."
            )
            return

        # One Gemini API call for the complete meeting analysis
        data = await asyncio.to_thread(
            analyze_meeting_once,
            transcript
        )

        # Save meeting history and extracted tasks
        saved_count = await asyncio.to_thread(
            save_meeting,
            data["meeting_name"],
            data["tasks"],
            data["summary"],
            transcript
        )

        if saved_count is None:
            await message.reply_text(
                "⚠️ This meeting was already saved. "
                "No duplicate records were added."
            )
            return

        # Build Telegram report
        result = f"📌 MEETING: {data['meeting_name']}\n\n"

        result += "📝 MEETING SUMMARY\n"
        result += data["summary"] + "\n\n"

        result += "✅ KEY DECISIONS\n"
        decisions = data["key_decisions"]
        result += (
            "\n".join(f"• {item}" for item in decisions)
            if decisions else "No key decisions identified."
        )
        result += "\n\n"

        result += "📋 ACTION ITEMS\n"

        if data["tasks"]:
            for index, task in enumerate(data["tasks"], start=1):
                result += f"\n{index}. {task['task']}\n"
                result += f"   Owner: {task['owner']}\n"
                result += f"   Deadline: {task['deadline']}\n"
                result += f"   Status: {task['status']}\n"
        else:
            result += "No action items identified.\n"

        result += "\n💡 RECOMMENDATIONS\n"
        recommendations = data["recommendations"]
        result += (
            "\n".join(f"• {item}" for item in recommendations)
            if recommendations else "No recommendations generated."
        )

        result += "\n\n📊 GOOGLE SHEETS\n"
        result += f"✅ {saved_count} task(s) saved.\n"
        result += "📚 Meeting history saved successfully."

        # Telegram message limit
        for i in range(0, len(result), 4000):
            await message.reply_text(result[i:i + 4000])

    except Exception as e:
        import traceback

        traceback.print_exc()

        await message.reply_text(
            f"❌ Error: {str(e)[:1000]}"
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