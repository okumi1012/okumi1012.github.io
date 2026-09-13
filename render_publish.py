"""One-shot Roblox place publisher for a temporary Render service."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hashlib
import json
import os
from pathlib import Path
import threading
import urllib.error
import urllib.request


UNIVERSE_ID = "8730094153"
PLACE_ID = "75610031228318"
PLACE_FILE = Path(__file__).with_name("SimpleClicker.rbxlx")
EXPECTED_SHA256 = "dd8a07c98d4e41093d0605f9e4f23ef43e855b4ca1e3d57f088a802a169e0c10"
STATUS = {
    "state": "starting",
    "universeId": UNIVERSE_ID,
    "placeId": PLACE_ID,
    "fileSha256": EXPECTED_SHA256,
}


def publish_once():
    key = os.environ.get("ROBLOX_API_KEY", "").strip()
    if not key:
        STATUS["state"] = "waiting_for_key"
        print(json.dumps(STATUS), flush=True)
        return

    try:
        payload = PLACE_FILE.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        if digest != EXPECTED_SHA256:
            raise ValueError("place file checksum mismatch")

        STATUS["state"] = "publishing"
        url = (
            "https://apis.roblox.com/universes/v1/"
            f"{UNIVERSE_ID}/places/{PLACE_ID}/versions?versionType=Published"
        )
        request = urllib.request.Request(
            url,
            data=payload,
            method="POST",
            headers={"x-api-key": key, "Content-Type": "application/xml"},
        )
        with urllib.request.urlopen(request, timeout=45) as response:
            result = json.load(response)
        version = result.get("versionNumber") if isinstance(result, dict) else None
        if type(version) is not int or version <= 0:
            raise ValueError("Roblox did not return a valid version number")
        STATUS.update({"state": "published", "versionNumber": version})
    except urllib.error.HTTPError as error:
        STATUS.update({"state": "error", "httpStatus": error.code})
    except Exception as error:
        STATUS.update({"state": "error", "errorType": type(error).__name__})

    print(json.dumps(STATUS), flush=True)


class StatusHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps(STATUS).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        return


if __name__ == "__main__":
    threading.Thread(target=publish_once, daemon=True).start()
    port = int(os.environ.get("PORT", "10000"))
    ThreadingHTTPServer(("0.0.0.0", port), StatusHandler).serve_forever()
