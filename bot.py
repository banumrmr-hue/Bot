import asyncio
import csv
import os
from datetime import datetime

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from playwright.async_api import async_playwright

BOT_TOKEN = os.getenv("BOT_TOKEN") or "YOUR_BOT_TOKEN"
OWNER = "@c0dealx"


WELCOME_TEXT = f"""
╔══════════════════╗
      HI2 CHECKER BOT
╚══════════════════╝

⚡ Fast & Accurate Checker
📧 Supports:
• @hi2.in
• @telemail.com

👑 Owner: {OWNER}

Send emails line-by-line.

Example:
abc@hi2.in
hello@telemail.com
"""


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME_TEXT)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = f"""
╔══════════════╗
      COMMANDS
╚══════════════╝

/start → Start bot
/help → Help menu
/ping → Bot speed
/about → Bot info

👑 Owner: {OWNER}
"""

    await update.message.reply_text(txt)


async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start = datetime.now()
    msg = await update.message.reply_text("⚡ Checking speed...")
    end = datetime.now()

    ms = (end - start).microseconds / 1000

    await msg.edit_text(f"⚡ Bot Speed: {ms:.0f} ms")


async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = f"""
╔══════════════════╗
      BOT INFO
╚══════════════════╝

🔥 Stylish HI2 Checker
⚡ Accurate Availability Detection
📄 CSV Export Supported
🚀 Fast Processing

👑 Owner: {OWNER}
"""

    await update.message.reply_text(txt)


async def check_email(page, email):
    try:
        email = email.strip().lower()

        if "@" not in email:
            return {
                "email": email,
                "status": "INVALID",
                "generated": "",
                "error": "Invalid Email"
            }

        prefix, domain_raw = email.split("@", 1)

        domain = "@" + domain_raw

        allowed = ["@hi2.in", "@telemail.com"]

        if domain not in allowed:
            return {
                "email": email,
                "status": "INVALID_DOMAIN",
                "generated": "",
                "error": "Unsupported Domain"
            }

        await page.click("button.tablinks:has-text('Customize')")

        await page.fill(
            "input.mailtext:not(.mailtextfix)",
            ""
        )

        await page.fill(
            "input.mailtext:not(.mailtextfix)",
            prefix
        )

        await page.select_option(
            "select.selcss",
            label=domain
        )

        await page.click("button.genbutton")

        await asyncio.sleep(3)

        generated = await page.input_value(
            "input.mailtext.mailtextfix"
        )

        generated = generated.strip().lower()

        status = "NOT_AVAILABLE"

        if generated == email:
            status = "AVAILABLE"

        return {
            "email": email,
            "generated": generated,
            "status": status,
            "error": ""
        }

    except Exception as e:
        return {
            "email": email,
            "generated": "",
            "status": "ERROR",
            "error": str(e)
        }


async def process_emails(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    emails = [
        line.strip().lower()
        for line in text.splitlines()
        if line.strip()
    ]

    if not emails:
        await update.message.reply_text("❌ No emails found.")
        return

    progress = await update.message.reply_text(
        f"""
╔════════════════╗
   CHECK STARTED
╚════════════════╝

📧 Total: {len(emails)}
⚡ Progress: 0/{len(emails)}
👑 {OWNER}
"""
    )

    results = []

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox"
            ]
        )

        page = await browser.new_page()

        await page.goto(
            "https://hi2.in/#/",
            wait_until="domcontentloaded",
            timeout=60000
        )

        await asyncio.sleep(5)

        for index, email in enumerate(emails, start=1):

            result = await check_email(page, email)

            results.append(result)

            await progress.edit_text(
                f"""
╔════════════════╗
   CHECK RUNNING
╚════════════════╝

⚡ Progress: {index}/{len(emails)}
📧 Current: {email}
👑 {OWNER}
"""
            )

            await asyncio.sleep(1)

        await browser.close()

    available = []
    not_available = []
    errors = []

    for r in results:

        if r["status"] == "AVAILABLE":
            available.append(r["email"])

        elif r["status"] == "NOT_AVAILABLE":
            not_available.append(r["email"])

        else:
            errors.append(r["email"])

    final_text = f"""
╔══════════════════╗
      FINAL RESULT
╚══════════════════╝

✅ AVAILABLE: {len(available)}
❌ NOT AVAILABLE: {len(not_available)}
⚠️ ERRORS: {len(errors)}

👑 Owner: {OWNER}
"""

    if available:
        final_text += "\n🔥 AVAILABLE EMAILS:\n\n"
        final_text += "\n".join(available[:50])

    await update.message.reply_text(final_text[:4000])

    filename = "results.csv"

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        writer.writerow([
            "email",
            "generated",
            "status",
            "error"
        ])

        for r in results:
            writer.writerow([
                r["email"],
                r["generated"],
                r["status"],
                r["error"]
            ])

    with open(filename, "rb") as f:
        await update.message.reply_document(
            document=f,
            caption=f"📄 Full Results CSV\n👑 {OWNER}"
        )

    os.remove(filename)


async def main():

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("about", about))

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            process_emails
        )
    )

    print("BOT STARTED")

    await app.run_polling()


if __name__ == "__main__":
    asyncio.run(main())
