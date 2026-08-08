"""AttestVault web app — stdlib HTTP server over the gated Vault.

Single external dependency: pycryptodome (AES for the Cleanverse transport).
Run:  python app.py   →  http://127.0.0.1:8990/
"""

from __future__ import annotations

import json
import os
import secrets as pysecrets
import sqlite3
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from attestvault.cleanverse import CleanverseClient, CleanverseError
from attestvault.vault import Vault

SECRETS = os.environ.get(
    "CLEANVERSE_SECRETS",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "cleanverse.secrets.json"),
)
CHAIN = os.environ.get("ATTESTVAULT_CHAIN", "monad")
DB = os.environ.get("ATTESTVAULT_DB", "attestvault.db")
PORT = int(os.environ.get("ATTESTVAULT_PORT", "8990"))
STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

creds = json.load(open(SECRETS, encoding="utf-8"))
client = CleanverseClient(creds["sandbox_api_id"], creds["sandbox_api_key"])
vault = Vault(client, CHAIN, db_path=DB)
lock = threading.Lock()

idb = sqlite3.connect(DB, check_same_thread=False)
idb.execute(
    "CREATE TABLE IF NOT EXISTS investors ("
    " address TEXT PRIMARY KEY, name TEXT, customer_id TEXT,"
    " cv_record_id TEXT, tier TEXT, tx_hash TEXT, frozen INTEGER DEFAULT 0)"
)
idb.commit()

_rails_cache: list | None = None


def rails() -> list:
    global _rails_cache
    if _rails_cache is None:
        _rails_cache = vault.registered_atokens()
    return _rails_cache


def investors() -> list[dict]:
    cur = idb.execute("SELECT address, name, customer_id, cv_record_id, tier, tx_hash, frozen FROM investors")
    cols = [c[0] for c in cur.description]
    out = []
    for r in cur.fetchall():
        d = dict(zip(cols, r))
        d["frozen"] = bool(d["frozen"])
        out.append(d)
    return out


def do_onboard(body: dict) -> dict:
    name = (body.get("name") or "Investor").strip()[:40]
    address = "0x" + pysecrets.token_hex(20)
    customer_id = "AV" + pysecrets.token_hex(9).upper()
    r = client.generate_apass(
        customer_id=customer_id, address=address, chain=CHAIN, expiration_time=1893456000,
        identity_data=[{"idType": "PASSPORT", "fullName": name, "idNumber": "AV" + pysecrets.token_hex(3).upper(),
                        "validUntil": "2030-12-31", "issuingCountryISO2": "JP"}],
    )
    row = {
        "name": name, "address": address, "customer_id": customer_id,
        "cv_record_id": r.get("cvRecordId"), "tier": r.get("tier"),
        "tx_hash": (r.get("wallet") or {}).get("txHash"),
    }
    idb.execute(
        "INSERT INTO investors (address, name, customer_id, cv_record_id, tier, tx_hash, frozen) VALUES (?,?,?,?,?,?,0)",
        (row["address"], row["name"], row["customer_id"], row["cv_record_id"], row["tier"], row["tx_hash"]),
    )
    idb.commit()
    return row


def do_freeze(body: dict) -> dict:
    address = body["address"]
    freeze = bool(body.get("freeze", True))
    r = client.set_apass_status(address, CHAIN, freeze=freeze, reason=body.get("reason", ""))
    idb.execute("UPDATE investors SET frozen = ? WHERE address = ?", (int(freeze), address))
    idb.commit()
    return {"tx_hash": (r or {}).get("txHash")}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _send(self, obj, status=200):
        raw = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            try:
                raw = open(os.path.join(STATIC, "index.html"), "rb").read()
            except FileNotFoundError:
                raw = b"<h1>AttestVault</h1><p>UI not built yet - API is live under /api/</p>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
        elif self.path == "/api/state":
            self._send({"chain": CHAIN, "rails": rails(), "holdings": vault.holdings(), "investors": investors()})
        elif self.path == "/api/audit":
            self._send(vault.audit(limit=100))
        else:
            self._send({"error": "not found"}, 404)

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(n).decode() or "{}")
            with lock:
                if self.path == "/api/onboard":
                    return self._send(do_onboard(body))
                if self.path == "/api/deposit":
                    return self._send(vault.deposit(body["token_address"], float(body.get("amount", 0))))
                if self.path == "/api/transfer":
                    return self._send(vault.transfer(body["atoken"], body["to_address"], float(body.get("amount", 0))))
                if self.path == "/api/freeze":
                    return self._send(do_freeze(body))
            self._send({"error": "not found"}, 404)
        except CleanverseError as e:
            self._send({"error": str(e)}, 502)
        except Exception as e:  # keep the demo server alive on bad input
            self._send({"error": repr(e)}, 400)


if __name__ == "__main__":
    print(f"AttestVault on http://127.0.0.1:{PORT}/  (chain={CHAIN})")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
