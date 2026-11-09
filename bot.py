import os
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
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
from sheets import (
    save_meeting,
    meeting_exists,
    get_all_tasks,
    update_task_status,
    get_deadline_tasks,
)

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

GROUP_CHAT_ID = os.getenv("TELEGRAM_GROUP_CHAT_ID")

TIMEZONE = os.getenv("TIMEZONE", "Asia/Kolkata")

TEST_INTERVAL = int(os.getenv("REMINDER_TEST_INTERVAL", "2"))


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


async def tasks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    del context
    message = update.message
    if message is None:
        return

    try:
        tasks = await asyncio.to_thread(get_all_tasks)

        if not tasks:
            await message.reply_text("📋 No tasks found in Google Sheets.")
            return

        result = "📋 YOUR TEAM TASKS\n\n"

        for index, task in enumerate(tasks, start=1):
            result += f"{index}. {task['task']}\n"
            result += f"   👤 Owner: {task['owner']}\n"
            result += f"   📅 Deadline: {task['deadline']}\n"
            result += f"   📌 Status: {task['status']}\n\n"

        for i in range(0, len(result), 4000):
            await message.reply_text(result[i:i + 4000])

    except Exception as e:
        print("TASKS ERROR:", str(e))
        await message.reply_text("❌ Could not retrieve tasks.")


async def show_filtered_tasks(update: Update, status: str) -> None:
    message = update.message

    if message is None:
        return

    try:
        tasks = await asyncio.to_thread(get_all_tasks)

        filtered_tasks = [
            task for task in tasks
            if task["status"].strip().lower() == status.lower()
        ]

        if not filtered_tasks:
            await message.reply_text(
                f"📋 No {status} tasks found."
            )
            return

        result = f"📋 {status.upper()} TASKS\n\n"

        for index, task in enumerate(filtered_tasks, start=1):
            result += f"{index}. {task['task']}\n"
            result += f"   👤 Owner: {task['owner']}\n"
            result += f"   📅 Deadline: {task['deadline']}\n"
            result += f"   📌 Status: {task['status']}\n\n"

        await message.reply_text(result)

    except Exception as e:
        print("FILTER TASKS ERROR:", str(e))
        await message.reply_text("❌ Could not retrieve tasks.")


async def pending_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    del context
    await show_filtered_tasks(update, "Pending")


async def completed_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    del context
    await show_filtered_tasks(update, "Completed")


async def upcoming_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    del context
    message = update.message

    if message is None:
        return

    try:
        data = await asyncio.to_thread(get_deadline_tasks)
        tasks = data["upcoming"]

        if not tasks:
            await message.reply_text("📅 No upcoming deadlines found.")
            return

        result = "📅 UPCOMING DEADLINES\n\n"

        for index, task in enumerate(tasks, start=1):
            result += f"{index}. {task['task']}\n"
            result += f"   👤 Owner: {task['owner']}\n"
            result += f"   📅 Deadline: {task['deadline']}\n"
            result += f"   📌 Status: {task['status']}\n\n"

        await message.reply_text(result)

    except Exception as e:
        print("UPCOMING ERROR:", str(e))
        await message.reply_text("❌ Could not retrieve deadlines.")


async def overdue_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    del context
    message = update.message

    if message is None:
        return

    try:
        data = await asyncio.to_thread(get_deadline_tasks)
        tasks = data["overdue"]

        if not tasks:
            await message.reply_text("🎉 No overdue tasks found!")
            return

        result = "⚠️ OVERDUE TASKS\n\n"

        for index, task in enumerate(tasks, start=1):
            result += f"{index}. {task['task']}\n"
            result += f"   👤 Owner: {task['owner']}\n"
            result += f"   📅 Deadline: {task['deadline']}\n"
            result += f"   📌 Status: {task['status']}\n\n"

        await message.reply_text(result)

    except Exception as e:
        print("OVERDUE ERROR:", str(e))
        await message.reply_text("❌ Could not retrieve overdue tasks.")



async def help_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    del context

    if update.message is None:
        return

    await update.message.reply_text(
        "🤖 MEETING ACTION BOT - COMMANDS\n\n"
        "/start - Start the bot\n"
        "/tasks - Show all tasks\n"
        "/pending - Show pending tasks\n"
        "/completed - Show completed tasks\n"
        "/status 1 Completed - Update task status\n"
        "/help - Show all commands"
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message

    if message is None:
        return

    args = context.args
    if args is None or len(args) != 2:
        await message.reply_text(
            "Usage: /status TASK_NUMBER STATUS\n\n"
            "Example: /status 2 Completed\n\n"
            "Allowed statuses:\n"
            "• Pending\n"
            "• In Progress\n"
            "• Completed"
        )
        return

    try:
        task_number = int(args[0])
        status_input = args[1].lower()

        status_map = {
            "pending": "Pending",
            "in": "In Progress",
            "completed": "Completed",
        }

        if status_input not in status_map:
            await message.reply_text(
                "❌ Invalid status. Use Pending, In or Completed."
            )
            return

        status = status_map[status_input]

        tasks = await asyncio.to_thread(get_all_tasks)

        if task_number < 1 or task_number > len(tasks):
            await message.reply_text("❌ Invalid task number.")
            return

        selected_task = tasks[task_number - 1]

        task_name = await asyncio.to_thread(
            update_task_status,
            selected_task["row"],
            status
        )

        await message.reply_text(
            f"✅ TASK STATUS UPDATED!\n\n"
            f"📋 Task: {task_name}\n"
            f"📌 New Status: {status}"
        )

    except ValueError:
        await message.reply_text(
            "❌ Please enter a valid task number."
        )
    except Exception as e:
        print("STATUS ERROR:", str(e))
        await message.reply_text("❌ Could not update task status.")


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
        meeting_date = datetime.now(ZoneInfo(TIMEZONE)).date().isoformat()
        data = await asyncio.to_thread(
            analyze_meeting_once,
            transcript,
            meeting_date,
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



async def send_deadline_reminder(
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    if not GROUP_CHAT_ID:
        print("REMINDER ERROR: Group Chat ID missing")
        return

    try:
        data = await asyncio.to_thread(get_deadline_tasks)

        upcoming = data["upcoming"]
        overdue = data["overdue"]

        message = "🔔 TEAM DEADLINE REMINDER\n\n"

        if overdue:
            message += "⚠️ OVERDUE TASKS\n"
            for task in overdue:
                message += (
                    f"• {task['task']}\n"
                    f"  Owner: {task['owner']}\n"
                    f"  Deadline: {task['deadline']}\n\n"
                )

        if upcoming:
            message += "📅 UPCOMING TASKS\n"
            for task in upcoming:
                message += (
                    f"• {task['task']}\n"
                    f"  Owner: {task['owner']}\n"
                    f"  Deadline: {task['deadline']}\n\n"
                )

        if not overdue and not upcoming:
            message += "🎉 No pending deadline tasks!"

        await context.bot.send_message(
            chat_id=int(GROUP_CHAT_ID),
            text=message,
        )

        print("Reminder sent successfully!")

    except Exception as e:
        print("REMINDER ERROR:", str(e))


def main():

    if not TOKEN:
        raise ValueError("Telegram token missing in .env")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("tasks", tasks_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("pending", pending_command))
    app.add_handler(CommandHandler("completed", completed_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("upcoming", upcoming_command))
    app.add_handler(CommandHandler("overdue", overdue_command))

    if app.job_queue is None:
        raise RuntimeError(
            "JobQueue is unavailable. Install python-telegram-bot[job-queue]."
        )
    
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