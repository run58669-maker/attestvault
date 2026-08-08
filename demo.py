"""AttestVault end-to-end demo against the Cleanverse sandbox on Monad.

Story:
  1. Discover the compliance rails on Monad (registered A-Tokens + contracts)
  2. Onboard investor Alice -> on-chain A-Pass (CVI)
  3. Deposit gate: registered A-Token accepted, unknown token rejected (CVA)
  4. Transfer gate: Alice passes verify_apass (code 4) -> transfer allowed
  5. Stranger without A-Pass -> transfer denied (code 2)
  6. Compliance officer freezes Alice's A-Pass on-chain -> same transfer now denied (code 3)
  7. Unfreeze -> allowed again. Audit log shows every decision with evidence.

Credentials are read from a local secrets file (never committed).
"""

import json
import os
import secrets
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
from attestvault.cleanverse import CleanverseClient
from attestvault.vault import Vault

SECRETS = os.environ.get("CLEANVERSE_SECRETS", r"C:\Users\86150\Desktop\脚本\secrets\cleanverse.json")
CHAIN = "monad"


def step(n, title):
    print(f"\n{'=' * 62}\n  STEP {n}: {title}\n{'=' * 62}")


def main():
    creds = json.load(open(SECRETS, encoding="utf-8"))
    cv = CleanverseClient(creds["sandbox_api_id"], creds["sandbox_api_key"])
    vault = Vault(cv, CHAIN, db_path="demo_run.db")

    step(1, "Discover compliance rails on Monad")
    rails = vault.registered_atokens()
    for t in rails:
        print(f"  A-Token {t['atoken']['symbol']} @ {t['atoken']['address']}")
        print(f"  access_core: {t['accesscore_address']}  apass contract: {t['apass_address']}")
    ausdc = rails[0]["atoken"]["address"]

    step(2, "Onboard investor Alice -> on-chain A-Pass (CVI)")
    alice = "0x" + secrets.token_hex(20)
    r = cv.generate_apass(
        customer_id="AVDEMOALICE" + secrets.token_hex(5).upper(),
        address=alice, chain=CHAIN, expiration_time=1893456000,
        identity_data=[{"idType": "PASSPORT", "fullName": "Alice Demo", "idNumber": "AV0001",
                        "validUntil": "2030-12-31", "issuingCountryISO2": "JP"}],
    )
    print(f"  Alice wallet: {alice}")
    print(f"  A-Pass created: cvRecordId={r['cvRecordId']} tier={r['tier']}")
    print(f"  on-chain tx: {r['wallet']['txHash']}")

    step(3, "Deposit gate (CVA): registered A-Token vs unknown token")
    d1 = vault.deposit(ausdc, 1000)
    print(f"  aUSDC deposit -> {d1['verdict']}")
    d2 = vault.deposit("0x" + secrets.token_hex(20), 500)
    print(f"  random token  -> {d2['verdict']}")

    step(4, "Transfer gate (CVI): Alice with valid A-Pass")
    t1 = vault.transfer(ausdc, alice, 250)
    print(f"  -> {t1['verdict']}")

    step(5, "Transfer gate: stranger without A-Pass")
    stranger = "0x" + secrets.token_hex(20)
    t2 = vault.transfer(ausdc, stranger, 250)
    print(f"  -> {t2['verdict']}")

    step(6, "Compliance officer freezes Alice's A-Pass on-chain")
    fr = cv.set_apass_status(alice, CHAIN, freeze=True, reason="sanctions review")
    print(f"  freeze tx: {fr.get('txHash')}")
    for attempt in range(6):
        time.sleep(5)
        t3 = vault.transfer(ausdc, alice, 250)
        print(f"  transfer retry -> {t3['verdict']}")
        if not t3["allowed"]:
            break

    step(7, "Unfreeze -> gate opens again")
    uf = cv.set_apass_status(alice, CHAIN, freeze=False)
    print(f"  unfreeze tx: {uf.get('txHash')}")
    for attempt in range(6):
        time.sleep(5)
        t4 = vault.transfer(ausdc, alice, 100)
        print(f"  transfer retry -> {t4['verdict']}")
        if t4["allowed"]:
            break

    step(8, "Audit log (every decision, with evidence)")
    for row in vault.audit(limit=12)[::-1]:
        mark = "✅" if row["allowed"] else "⛔"
        print(f"  {mark} [{row['gate']:8}] {row['subject'][:20]}…  {row['verdict']}")

    print("\nDemo complete.")


if __name__ == "__main__":
    main()
