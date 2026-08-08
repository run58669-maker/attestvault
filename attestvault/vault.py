"""AttestVault core: a vault whose deposits and transfers are gated by
Cleanverse compliance rails.

Deposit gate  (CVA): only assets registered as A-Tokens on the target chain
                     may enter the vault.
Transfer gate (CVI): an outbound transfer is constructed only if the
                     counterparty wallet passes verify_apass (code 4).
Every gate decision is appended to an audit log with the on-chain evidence
that produced it.
"""

from __future__ import annotations

import json
import sqlite3
import time

from .cleanverse import CleanverseClient, CleanverseError, VERIFY_OK

VERDICT_TEXT = {
    1: "DENY: asset is not a registered A-Token",
    2: "DENY: counterparty has no A-Pass identity",
    3: "DENY: counterparty A-Pass is frozen or expired",
    4: "ALLOW: valid A-Pass, transfer permitted",
}


class Vault:
    def __init__(self, client: CleanverseClient, chain: str, db_path: str = "attestvault.db"):
        self.cv = client
        self.chain = chain
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS audit_log ("
            " id INTEGER PRIMARY KEY AUTOINCREMENT, ts INTEGER, gate TEXT,"
            " subject TEXT, verdict TEXT, allowed INTEGER, evidence TEXT)"
        )
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS holdings ("
            " atoken TEXT PRIMARY KEY, symbol TEXT, origin_token TEXT, amount REAL)"
        )
        self.db.commit()

    def _log(self, gate: str, subject: str, verdict: str, allowed: bool, evidence: dict) -> dict:
        row = {
            "ts": int(time.time()), "gate": gate, "subject": subject,
            "verdict": verdict, "allowed": allowed, "evidence": evidence,
        }
        self.db.execute(
            "INSERT INTO audit_log (ts, gate, subject, verdict, allowed, evidence) VALUES (?,?,?,?,?,?)",
            (row["ts"], gate, subject, verdict, int(allowed), json.dumps(evidence)),
        )
        self.db.commit()
        return row

    # -- deposit gate (CVA) ------------------------------------------------

    def registered_atokens(self) -> list[dict]:
        data = self.cv.deposit_atoken_list(self.chain)
        return data.get("tokens", [])

    def deposit(self, token_address: str, amount: float) -> dict:
        """Accept a deposit only if token_address is a registered A-Token."""
        for t in self.registered_atokens():
            at = t.get("atoken") or {}
            if at.get("address", "").lower() == token_address.lower():
                self.db.execute(
                    "INSERT INTO holdings (atoken, symbol, origin_token, amount) VALUES (?,?,?,?)"
                    " ON CONFLICT(atoken) DO UPDATE SET amount = amount + excluded.amount",
                    (at["address"], at.get("symbol", ""), (t.get("origin_token") or {}).get("address", ""), amount),
                )
                self.db.commit()
                return self._log("deposit", token_address, f"ALLOW: registered A-Token {at.get('symbol')}", True,
                                 {"atoken": at, "accesscore": t.get("accesscore_address")})
        return self._log("deposit", token_address, VERDICT_TEXT[1], False, {"chain": self.chain})

    # -- transfer gate (CVI) -----------------------------------------------

    def transfer(self, atoken: str, to_address: str, amount: float) -> dict:
        """Gate an outbound transfer on the counterparty's A-Pass. The
        transfer is only *constructed* after code 4 — a denial means no
        transaction ever exists, not a revert."""
        try:
            v = self.cv.verify_apass(to_address, self.chain, atoken)
        except CleanverseError as e:
            # Fail closed: any verification error is a denial. In sandbox
            # practice a frozen A-Pass surfaces as an APassNotActive contract
            # revert (business code 0002) rather than the documented code 3.
            if "APassNotActive" in str(e):
                verdict = "DENY: counterparty A-Pass is frozen (on-chain APassNotActive)"
            else:
                verdict = f"DENY (fail-closed): verification error — {e}"
            return self._log("transfer", to_address, verdict, False,
                             {"error": str(e), "atoken": atoken, "amount": amount})
        code = v.get("code")
        verdict = VERDICT_TEXT.get(code, f"DENY: unknown verify code {code}")
        allowed = code == VERIFY_OK
        if allowed:
            self.db.execute("UPDATE holdings SET amount = amount - ? WHERE atoken = ?", (amount, atoken))
            self.db.commit()
        return self._log("transfer", to_address, verdict, allowed,
                         {"verify_response": v, "atoken": atoken, "amount": amount})

    # -- views -------------------------------------------------------------

    def holdings(self) -> list[dict]:
        cur = self.db.execute("SELECT atoken, symbol, origin_token, amount FROM holdings")
        return [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]

    def audit(self, limit: int = 50) -> list[dict]:
        cur = self.db.execute(
            "SELECT ts, gate, subject, verdict, allowed, evidence FROM audit_log ORDER BY id DESC LIMIT ?", (limit,))
        rows = []
        for r in cur.fetchall():
            d = dict(zip([c[0] for c in cur.description], r))
            d["evidence"] = json.loads(d["evidence"])
            rows.append(d)
        return rows
