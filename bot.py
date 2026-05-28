import asyncio
import csv
import os
from datetime import datetime

from telegram import Update
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
📧 Domains:
• @hi2.in
• @telemail.com

👑 Owner: {OWNER}

Send emails line-by-line.

Example:

test@hi2.in
hello@telemail.com
"""


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME_TEXT)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"""
╔══════════════╗
      COMMANDS
╚══════════════╝

/start → Start Bot
/help → Help Menu
/ping → Bot Speed
/about → Bot Info

👑 {OWNER}
"""
    )


async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = datetime.now()

    msg = await update.message.reply_text("⚡ Checking speed...")

    end_time = datetime.now()

    ms = (end_time - start_time).microseconds / 1000

    await msg.edit_text(f"⚡ Speed: {ms:.0f} ms")


async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"""
╔══════════════════╗
      BOT INFO
╚══════════════════╝

🔥 Stylish HI2 Checker
⚡ Accurate Detection
📄 CSV Export
🚀 Fast Checking

👑 Owner: {OWNER}
"""
    )


async def check_email(page, email):
    try:
        email = email.strip().lower()

        if "@" not in email:
            return {
                "email": email,
                "generated": "",
                "status": "INVALID",
                "error": "Invalid email"
            }

        prefix, domain_raw = email.split("@", 1)

        domain = "@" + domain_raw

        allowed_domains = [
            "@hi2.in",
            "@telemail.com"
        ]

        if domain not in allowed_domains:
            return {
                "email": email,
                "generated": "",
                "status": "INVALID_DOMAIN",
                "error": "Unsupported domain"
            }

        await page.click(
            "button.tablinks:has-text('Customize')"
        )

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

        await page.locator(
            "button.genbutton"
        ).click(timeout=10000)

        await asyncio.sleep(5)

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


async def process_emails(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    text = update.message.text

    emails = [
        line.strip().lower()
        for line in text.splitlines()
        if line.strip()
    ]

    if not emails:
        await update.message.reply_text(
            "❌ No emails found."
        )
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
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled"
            ]
        )

        page = await browser.new_page()

        await page.goto(
            "https://hi2.in/#/",
            wait_until="networkidle",
            timeout=120000
        )

        await asyncio.sleep(8)

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

👑 {OWNER}
"""

    if available:
        final_text += "\n🔥 AVAILABLE EMAILS:\n\n"
        final_text += "\n".join(available[:50])

    await update.message.reply_text(
        final_text[:4000]
    )

    filename = "results.csv"

    with open(
        filename,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

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

app.run_polling()
