import os, asyncio
from telethon import TelegramClient, events
from telethon.sessions import StringSession

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_STRING = os.environ["SESSION_STRING"]
SOURCE = os.environ["SOURCE"]
TARGET = os.environ["TARGET"]
MODE = os.environ.get("MODE", "copy").lower()

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

async def send_copy(tgt, msg):
    text = msg.raw_text or ""
    if msg.media:
        try:
            file = await client.download_media(msg.media, file=bytes)
            return await client.send_file(tgt, file=file, caption=text or None)
        except Exception as e:
            print("[COPY] media fail:", e)
    if text:
        try:
            return await client.send_message(tgt, text)
        except Exception as e:
            print("[COPY] text fail:", e)
    return None

async def main():
    src = await client.get_entity(SOURCE)
    tgt = await client.get_entity(TARGET)
    print(f"[START] SOURCE={src} → TARGET={tgt} | MODE={MODE}")

    @client.on(events.NewMessage(chats=src))
    async def handler(ev):
        try:
            if MODE == "forward":
                await client.forward_messages(tgt, ev.message)
            else:
                await send_copy(tgt, ev.message)
        except Exception as e:
            print("[REALTIME] fail:", e)

    await client.run_until_disconnected()

if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())
