# AttestVault — one-page summary

**Compliance-gated vault for real-world assets on Cleanverse rails · Monad**
Team: AttestVault (solo builder, Wei Fang) · Repo: github.com/run58669-maker/attestvault (Apache-2.0) · Track: RWA

## Problem

Institutions that custody tokenized real-world assets fail compliance in two directions. Inbound: they accept tokens whose issuance and rule-set they cannot verify. Outbound: they discover a counterparty was sanctioned, frozen, or unverified only *after* a transfer exists on-chain — and an on-chain revert, or worse a completed transfer, is already a reportable event. Compliance teams need transfers that are impossible to construct, not transfers that fail loudly.

## Solution

AttestVault is a vault with a door policy on both sides, enforced by Cleanverse before any transaction is built:

- **Deposit gate (CVA / A-Token).** An asset enters the vault only if it resolves to a registered Cleanverse A-Token on the target chain (`query_deposit_atoken_list`). Unknown contracts are rejected at the door with a logged verdict.
- **Transfer gate (CVI / A-Pass).** An outbound transfer is constructed only after the counterparty wallet passes `verify_apass` (result code 4). No A-Pass, an expired A-Pass, or a frozen A-Pass means the transaction is *never emitted* — fail closed, nothing to unwind, nothing to report.
- **Compliance console.** Officers onboard investors (`generate_apass` → on-chain A-Pass with identity documents), freeze or reinstate them (`update_status` → on-chain tx), and watch every gate decision land in an audit log that stores the full Cleanverse evidence — including transaction hashes — for each ALLOW/DENY.

The signature demo is the **freeze flip**: a transfer to an investor passes, the officer freezes their A-Pass (on-chain tx), and the same transfer is denied within seconds — then reinstated just as fast.

## CVI · CVA integration points

| # | Integration | Endpoint(s) | Depth |
|---|---|---|---|
| 1 | Investor onboarding → on-chain identity | `generate_apass` (AES-encrypted body) | Real A-Pass minted on Monad, txHash captured |
| 2 | Freeze / reinstate lifecycle | `update_status` | On-chain status change drives the gate live |
| 3 | Transfer gating | `verify_apass` | All 4 result codes mapped to vault verdicts |
| 4 | Asset registry gating | `query_deposit_atoken_list` | Deposits restricted to registered A-Tokens; access_core / A-Pass contract discovery |
| 5 | Funding & evidence | `faucet`, `query_txs` | Sandbox funding and audit cross-checks |

**Observed-behavior handling:** the docs specify verify code 3 for a frozen A-Pass; on Monad the sandbox actually surfaces a contract-level `APassNotActive` revert as a business error. AttestVault treats *any* verification failure as a denial (fail closed) and records the raw revert as evidence — integration at the contract-behavior level, not just the happy path.

## Deployed chain(s)

**Monad** (Cleanverse sandbox/UAT rails: aUSDC A-Token `0xaC08…f20D`, access_core `0x8F11…6EcC`, A-Pass contract `0xbA82…58B9`). All A-Pass mints, freezes, and reinstates in the demo are real Monad transactions. The client is chain-parameterized; the same vault runs unchanged on any of the ten Cleanverse-supported networks.

## Build

Python stdlib HTTP server + single-file dashboard (zero frontend dependencies); one external package (pycryptodome) for the AES transport Cleanverse requires. Every commit in the hacking window. Scalability path: the vault core is a library — the same gates drop into an exchange withdrawal pipeline or a custodian's signing service, and rule changes (tier, group, country lists) propagate without code changes because they live on the A-Token, not in the vault.
