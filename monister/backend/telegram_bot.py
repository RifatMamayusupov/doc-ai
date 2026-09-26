"""
Monister Telegram Bot — Hujjatlarni Telegram orqali yetkazish.

Foydalanish:
    from telegram_bot import send_document_to_user

    # Username orqali
    await send_document_to_user("@username", "/path/to/file.pdf")

    # Chat ID orqali
    await send_document_to_user("123456789", "/path/to/file.pdf")
"""

import os
import asyncio
from pathlib import Path
from typing import Optional

# Telegram bot token from env or admin config
TELEGRAM_BOT_TOKEN: Optional[str] = os.environ.get("TELEGRAM_BOT_TOKEN")

# Store for username → chat_id mapping (in-memory, persists per session)
_username_cache: dict[str, int] = {}


def set_bot_token(token: str) -> None:
    """Set or update the Telegram bot token."""
    global TELEGRAM_BOT_TOKEN
    TELEGRAM_BOT_TOKEN = token


def get_bot_token() -> Optional[str]:
    """Get current bot token."""
    return TELEGRAM_BOT_TOKEN


async def send_document_to_user(
    recipient: str,
    file_path: str,
    caption: str = "",
    bot_token: str = None,
) -> dict:
    """
    Send a document to a Telegram user.

    Args:
        recipient: Telegram username (@user) or chat_id (numeric string)
        file_path: Absolute path to the file to send
        caption: Optional caption for the document
        bot_token: Override bot token (uses global if not set)

    Returns:
        dict with status, message, and optional details
    """
    token = bot_token or TELEGRAM_BOT_TOKEN

    if not token:
        return {
            "status": "error",
            "message": "Telegram bot token sozlanmagan. Admin panelda yoki TELEGRAM_BOT_TOKEN env-da kiriting.",
        }

    if not file_path or not os.path.exists(file_path):
        return {
            "status": "error",
            "message": f"Fayl topilmadi: {file_path}",
        }

    try:
        import httpx
    except ImportError:
        # Fallback to urllib if httpx not available
        return await _send_with_urllib(token, recipient, file_path, caption)

    return await _send_with_httpx(token, recipient, file_path, caption)


async def _send_with_httpx(
    token: str, recipient: str, file_path: str, caption: str
) -> dict:
    """Send document using httpx (async)."""
    import httpx

    chat_id = await _resolve_chat_id(token, recipient)
    if not chat_id:
        return {
            "status": "error",
            "message": f"Telegram foydalanuvchi topilmadi: {recipient}. "
                       f"Foydalanuvchi avval botga /start yuborishi kerak.",
        }

    url = f"https://api.telegram.org/bot{token}/sendDocument"
    fname = Path(file_path).name

    async with httpx.AsyncClient(timeout=60) as client:
        with open(file_path, "rb") as f:
            files = {"document": (fname, f)}
            data = {"chat_id": chat_id}
            if caption:
                data["caption"] = caption[:1024]

            response = await client.post(url, data=data, files=files)

    if response.status_code == 200:
        result = response.json()
        if result.get("ok"):
            return {
                "status": "success",
                "message": f"✅ '{fname}' hujjati {recipient} ga yuborildi!",
                "telegram_message_id": result.get("result", {}).get("message_id"),
            }

    return {
        "status": "error",
        "message": f"Telegram xatosi: {response.text[:200]}",
    }


async def _send_with_urllib(
    token: str, recipient: str, file_path: str, caption: str
) -> dict:
    """Fallback: send using urllib (sync, wrapped in asyncio)."""
    import urllib.request
    import urllib.parse
    import json

    chat_id = await _resolve_chat_id(token, recipient)
    if not chat_id:
        return {
            "status": "error",
            "message": f"Telegram foydalanuvchi topilmadi: {recipient}",
        }

    url = f"https://api.telegram.org/bot{token}/sendDocument"
    fname = Path(file_path).name

    # Build multipart form
    boundary = "----MonisterBoundary"
    body = []

    # chat_id field
    body.append(f"--{boundary}".encode())
    body.append(b'Content-Disposition: form-data; name="chat_id"')
    body.append(b"")
    body.append(str(chat_id).encode())

    # caption field
    if caption:
        body.append(f"--{boundary}".encode())
        body.append(b'Content-Disposition: form-data; name="caption"')
        body.append(b"")
        body.append(caption[:1024].encode())

    # document file
    body.append(f"--{boundary}".encode())
    body.append(f'Content-Disposition: form-data; name="document"; filename="{fname}"'.encode())
    body.append(b"Content-Type: application/octet-stream")
    body.append(b"")
    with open(file_path, "rb") as f:
        body.append(f.read())

    body.append(f"--{boundary}--".encode())

    data = b"\r\n".join(body)

    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )

    try:
        resp = urllib.request.urlopen(req, timeout=60)
        result = json.loads(resp.read())
        if result.get("ok"):
            return {
                "status": "success",
                "message": f"✅ '{fname}' hujjati {recipient} ga yuborildi!",
            }
    except Exception as e:
        return {"status": "error", "message": f"Yuborish xatosi: {str(e)}"}

    return {"status": "error", "message": "Noma'lum xato"}


async def _resolve_chat_id(token: str, recipient: str) -> Optional[int]:
    """
    Resolve recipient to a Telegram chat_id.
    
    - If numeric → use directly as chat_id
    - If @username → look up from cache or getUpdates
    """
    # Clean up username
    recipient = recipient.strip()

    # Numeric chat_id
    try:
        return int(recipient)
    except ValueError:
        pass

    # Remove @ prefix
    username = recipient.lstrip("@").lower()

    # Check cache
    if username in _username_cache:
        return _username_cache[username]

    # Try to find from getUpdates
    try:
        import httpx
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"https://api.telegram.org/bot{token}/getUpdates",
                params={"limit": 100},
            )
            if resp.status_code == 200:
                data = resp.json()
                for update in data.get("result", []):
                    msg = update.get("message", {})
                    user = msg.get("from", {})
                    uname = (user.get("username") or "").lower()
                    chat_id = msg.get("chat", {}).get("id")

                    if uname and chat_id:
                        _username_cache[uname] = chat_id

                        if uname == username:
                            return chat_id
    except Exception:
        pass

    return None


async def test_bot_token(token: str) -> dict:
    """Test if a bot token is valid by calling getMe."""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"https://api.telegram.org/bot{token}/getMe")
            if resp.status_code == 200:
                data = resp.json()
                if data.get("ok"):
                    bot = data["result"]
                    return {
                        "status": "success",
                        "bot_name": bot.get("first_name"),
                        "bot_username": bot.get("username"),
                    }
        return {"status": "error", "message": "Token noto'g'ri"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
