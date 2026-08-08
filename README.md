# AttestVault

**Compliance-gated vault for real-world assets, built on Cleanverse rails (A-Pass identity + A-Token assets) on Monad.**

Built solo inside the Cleanverse Build: Trusted Assets Hackathon 48h window (Aug 8–9, 2026 UTC) · Track: RWA · License: Apache-2.0

## The problem

Institutions that custody tokenized RWAs fail compliance in two directions: inbound, they accept tokens whose issuance and rules they cannot verify; outbound, they find out a counterparty was frozen or unverified only after a transaction exists on-chain. A reverted — or worse, completed — non-compliant transfer is already a reportable incident. Compliance teams need violating transfers to be **impossible to construct**, not loud when they fail.

## What AttestVault does

```
            ┌─────────────────────────── AttestVault ──────────────────────────┐
 deposit ──▶│ Deposit gate (CVA)              Transfer gate (CVI)              │──▶ transfer
            │  asset resolves to a            counterparty passes verify_apass │
            │  registered A-Token?            (code 4) at this exact moment?   │
            │        │no                              │no                      │
            │        ▼                                ▼                        │
            │   DENY, logged                DENY, logged — the transaction     │
            │                               is never emitted (fail closed)     │
            └───────────────┬──────────────────────────┬──────────────────────┘
                            ▼                          ▼
                       audit log: every ALLOW/DENY + on-chain evidence (txHash)
```

- **Deposit gate (CVA / A-Token):** an asset enters the vault only if it resolves to a registered Cleanverse A-Token on the chain (`query_deposit_atoken_list`). Unknown contracts are turned away at the door.
- **Transfer gate (CVI / A-Pass):** an outbound transfer is constructed only after the counterparty passes `verify_apass`. No A-Pass, expired, or frozen → the transaction never exists.
- **Compliance console:** onboard investors (`generate_apass` → on-chain A-Pass), freeze/reinstate (`update_status` → on-chain tx), and watch every decision land in the audit log with full Cleanverse evidence.

The signature move is the **freeze flip**: a transfer to an investor passes → the officer freezes their A-Pass (real on-chain tx) → the same transfer is denied within seconds → reinstate, and it opens again.

## Run it

```bash
pip install pycryptodome            # the single external dependency

# Credentials: put your Cleanverse sandbox api-id/api-key (issued with your
# hackathon registration) in cleanverse.secrets.json next to app.py:
#   {"sandbox_api_id": "...", "sandbox_api_key": "..."}
# or point CLEANVERSE_SECRETS at the file:
export CLEANVERSE_SECRETS=path/to/cleanverse.json        # bash
# $env:CLEANVERSE_SECRETS = "path\to\cleanverse.json"    # PowerShell

python demo.py                      # 8-step end-to-end story in the terminal (~60s)
python app.py                       # web console → http://127.0.0.1:8990/
```

`demo.py` runs the whole story against the live sandbox: rail discovery → investor onboarding (on-chain) → both gates, allow and deny → freeze flip → reinstate → audit dump. Every ALLOW/DENY it prints is backed by a real Monad transaction hash shown in the output.

## Architecture

| Piece | File | Notes |
|---|---|---|
| Cleanverse client | `attestvault/cleanverse.py` | AES-CBC/PKCS5 encrypted transport (zero IV, base64 api-key) per API v5.6; A-Pass, A-Token, validator, query and faucet endpoints |
| Vault core | `attestvault/vault.py` | The two gates + sqlite audit log; a plain library with no web dependency |
| Web console | `app.py` | Python stdlib HTTP server (no framework), JSON API |
| Dashboard | `static/index.html` | Single file, zero external assets — works offline |

## Deployed chain

**Monad**, on Cleanverse sandbox/UAT rails: aUSDC A-Token `0xaC0893567D43C3E7e6e35a72803df05416C1f20D`, access_core `0x8F118338a1fa41E7Fa86Be19A4e8B99Ed58A6EcC`, A-Pass contract `0xbA82D189540CaC9DC6FF46B6837CaC1BFdEC58B9`. The client is chain-parameterized; the same vault runs unchanged on any of the ten networks Cleanverse supports.

## Honest notes & limitations

- Everything runs against the Cleanverse **sandbox/UAT** environment provided for the hackathon — this is not a production deployment.
- Vault balances are library-level bookkeeping used to demonstrate the gates; moving the held funds themselves on-chain (deposit sweep / settlement) is the natural next layer and out of 48h scope.
- **Observed vs documented behavior:** the docs return verify code 3 for a frozen A-Pass; on Monad the sandbox surfaces a contract-level `APassNotActive` revert as a business error instead. AttestVault treats any verification failure as a denial (fail closed) and stores the raw revert as evidence.
- The A-Pass tier assigned by the sandbox for new registrations (tier 50) is taken as-is; tier/group/country rule authoring is exercised through the A-Token rule object.

## Security

No credentials live in this repository. The API key is read from a local secrets file (path via `CLEANVERSE_SECRETS`); request bodies are encrypted with AES per the Cleanverse spec; the api-key itself is never sent over the wire.
