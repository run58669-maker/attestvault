"""Cleanverse Cooperate API client (A-Pass / A-Token / queries).

Auth: `api-id` header. Write endpoints require the JSON body to be AES-CBC
encrypted (PKCS5, 16 zero-byte IV) with the base64-decoded api-key and sent
as {"data": "<base64 ciphertext>"} — per Cleanverse API v5.6 docs.
"""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request

from Crypto.Cipher import AES

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"

# verify_apass data.code meanings (docs: Verify A-Pass)
VERIFY_ATOKEN_NOT_FOUND = 1
VERIFY_NO_APASS = 2
VERIFY_APASS_BLOCKED = 3  # expired or frozen
VERIFY_OK = 4


class CleanverseError(RuntimeError):
    def __init__(self, code: str, message: str, payload=None):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.payload = payload


class CleanverseClient:
    def __init__(self, api_id: str, api_key_b64: str, base_url: str = "https://uatapi.cleanverse.com/api/cooperate"):
        self.api_id = api_id
        self.key = base64.b64decode(api_key_b64)
        self.base = base_url.rstrip("/")

    # -- transport ---------------------------------------------------------

    def _encrypt(self, obj: dict) -> dict:
        raw = json.dumps(obj, separators=(",", ":")).encode()
        pad = 16 - len(raw) % 16
        raw += bytes([pad]) * pad
        ct = AES.new(self.key, AES.MODE_CBC, b"\x00" * 16).encrypt(raw)
        return {"data": base64.b64encode(ct).decode()}

    def _post(self, path: str, body: dict, encrypted: bool = False) -> dict:
        payload = self._encrypt(body) if encrypted else body
        req = urllib.request.Request(
            self.base + path,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json", "api-id": self.api_id, "User-Agent": UA, "Accept": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                out = json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            raise CleanverseError(str(e.code), e.read().decode()[:300])
        except (OSError, ValueError) as e:
            # network failure / timeout / bad JSON — surface as a client error
            # so callers' fail-closed handling applies uniformly
            raise CleanverseError("transport", f"{type(e).__name__}: {e}")
        if out.get("code") != "0000":
            raise CleanverseError(out.get("code", "?"), out.get("message", ""), out.get("data"))
        return out.get("data")

    # -- CVI: A-Pass (identity) -------------------------------------------

    def generate_apass(self, customer_id: str, address: str, chain: str, expiration_time: int,
                       identity_data=None, override: bool = False, sub_tier: int | None = None,
                       sub_group: str | None = None) -> dict:
        body = {
            "customerId": customer_id,
            "override": override,
            "expirationTime": expiration_time,
            "wallet": {"address": address, "chain": chain},
        }
        if identity_data:
            body["identityDataList"] = identity_data
        if sub_tier is not None:
            body["subTier"] = sub_tier
        if sub_group is not None:
            body["subGroup"] = sub_group
        return self._post("/generate_apass", body, encrypted=True)

    def set_apass_status(self, address: str, chain: str, freeze: bool, reason: str = "", customer_id: str | None = None) -> dict:
        body = {"status": "2" if freeze else "1", "wallet": {"chain": chain, "address": address}}
        if reason:
            body["blacklistReason"] = reason
        if customer_id:
            body["customerId"] = customer_id
        return self._post("/update_status", body, encrypted=True)

    def query_apass(self, address: str, chain: str) -> dict:
        return self._post("/query_apass", {"chain": chain, "address": address})

    def verify_apass(self, address: str, chain: str, atoken: str) -> dict:
        return self._post("/verify_apass", {"chain": chain, "atoken": atoken, "address": address})

    # -- CVA: A-Token (asset) ---------------------------------------------

    def launch_atoken(self, chain: str, name: str, symbol: str, decimals: int, admin_address: str,
                      rule: dict, icon: str, callback_url: str | None = None) -> dict:
        body = {
            "chain": chain, "token_name": name, "token_symbol": symbol, "decimals": decimals,
            "admin_address": admin_address, "rule": rule, "icon": icon,
        }
        if callback_url:
            body["callback_url"] = callback_url
        return self._post("/atoken/launch", body, encrypted=True)

    def query_apply_status(self, request_id: str) -> dict:
        req = urllib.request.Request(
            f"{self.base}/atoken/query_apply_status/{request_id}",
            headers={"api-id": self.api_id, "User-Agent": UA, "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            out = json.loads(r.read().decode())
        if out.get("code") != "0000":
            raise CleanverseError(out.get("code", "?"), out.get("message", ""), out.get("data"))
        return out.get("data")

    # -- queries / utilities ----------------------------------------------

    def deposit_atoken_list(self, chain: str) -> dict:
        return self._post("/query_deposit_atoken_list", {"chain": chain})

    def query_txs(self, address: str, chain: str, **filters) -> dict:
        return self._post("/query_txs", {"chain": chain, "address": address, **filters})

    def faucet(self, chain: str, symbol: str, deposit_address: str, amount: int) -> dict:
        return self._post("/faucet", {"chain": chain, "symbol": symbol, "depositAddress": deposit_address, "amount": amount})
