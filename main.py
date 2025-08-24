# main.py
import os, sys, asyncio
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# -------- ENV --------
def must(name: str) -> str:
    v = os.getenv(name)
    if not v or not str(v).strip():
        print(f"[FATAL] manca la Config Var: {name}")
        sys.exit(1)
    return v.strip()

API_ID = int(must("API_ID"))
API_HASH = must("API_HASH")
SESSION_STRING = must("SESSION_STRING")
SOURCE_RAW = must("SOURCE")   # -100..., @username, o link t.me/...
TARGET_RAW = must("TARGET")   # -100..., @username, o link t.me/...
MODE = os.getenv("MODE", "copy").strip().lower()  # "copy" (default) o "forward"

# -------- PARSE PEER (ID, @username, link t.me) --------
def parse_peer(s: str):
    s = (s or "").strip().strip("'").strip('"')
    if not s:
        return s
    # link t.me
    if "t.me/" in s:
        path = s.split("t.me/")[-1].strip("/")
        if path.startswith("c/"):
            # t.me/c/<internal>/<post> -> -100<internal>
            parts = path.split("/")
            if len(parts) >= 2 and parts[1].isdigit():
                return int("-100" + parts[1])
        user = path.split("/")[0]
        return user if user.startswith("@") else f"@{user}"
    # numerico?
    try:
        return int(s)  # -100...
    except ValueError:
        return s if s.startswith("@") else f"@{s}"

SOURCE = parse_peer(SOURCE_RAW)
TARGET = parse_peer(TARGET_RAW)

# -------- CLIENT --------
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

async def resolve_or_die(peer_raw, label):
    try:
        ent = await client.get_entity(peer_raw)
        title = getattr(ent, "title", getattr(ent, "username", getattr(ent, "id", "?")))
        print(f"[OK] {label} risolto: {title} ({getattr(ent,'id','?')})")
        return ent
    except Exception as e:
        print(f"[FATAL] Impossibile risolvere {label}={peer_raw} → {e}")
        print("       • Assicurati che l'account della SESSION_STRING sia iscritto a quel canale/gruppo.")
        print("       • Per canali pubblici puoi usare @username o link t.me.")
        sys.exit(1)

async def copy_message(target, ev_msg, allow_media=True):
    txt = ev_msg.message or ""
    if ev_msg.media and allow_media:
        try:
            data = await client.download_media(ev_msg.media, file=bytes)
            await client.send_file(target, file=data, caption=txt or None)
            return "media"
        except Exception as e:
            print("[WARN] copia media fallita, passo al testo:", e)
    if txt:
        await client.send_message(target, txt)
        return "text"
    return "none"

async def main():
    me = await client.get_me()
    print(f"[START] Logged in as {getattr(me, 'username', me.id)} | MODE={MODE}")

    src = await resolve_or_die(SOURCE, "SOURCE")
    tgt = await resolve_or_die(TARGET, "TARGET")

    # Rileva contenuti protetti (anti-forward)
    is_protected = bool(getattr(src, "noforwards", False) or getattr(src, "has_protected_content", False))
    print(f"[INFO] SOURCE protected content: {is_protected}")

    @client.on(events.NewMessage(chats=src))
    async def handler(ev):
        try:
            if MODE == "forward" and not is_protected:
                await client.forward_messages(tgt, ev.message)
                print(f"[OK] forwarded (id={ev.message.id})")
            else:
                kind = await copy_message(tgt, ev.message, allow_media=(not is_protected))
                note = " (text-only: protected)" if (is_protected and ev.message.media) else ""
                print(f"[OK] copied: {kind}{note} (id={ev.message.id})")
        except Exception as e:
            print("[ERR] relay failed:", e)

    print("[READY] In ascolto...")
    await client.run_until_disconnected()

if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())
