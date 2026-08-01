import asyncio
import json
import os
from http.server import BaseHTTPRequestHandler

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from svetlyachok_bot import (
    SVETLYACHOK_BOT_TOKEN,
    handle_callback,
    handle_message,
    start,
)


def build_application():
    app = Application.builder().token(SVETLYACHOK_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )
    return app


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        secret = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
        received = self.headers.get(
            "X-Telegram-Bot-Api-Secret-Token", ""
        )

        if secret and received != secret:
            self.send_response(403)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length))
        asyncio.run(self.process_update(payload))

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    @staticmethod
    async def process_update(payload):
        app = build_application()
        async with app:
            update = Update.de_json(payload, app.bot)
            await app.process_update(update)

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status": "ok"}')
