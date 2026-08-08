# AttestVault

**Compliance-gated vault for real-world assets, built on Cleanverse A-Pass (identity) + A-Token (asset) rails on Monad.**

Institutions tokenizing real-world assets fear two things: receiving assets with no verifiable provenance, and sending value to counterparties they are not allowed to touch. AttestVault is a vault with a door policy on both sides:

- **Deposit gate (CVA / A-Token):** an asset enters the vault only after it is registered and rule-checked as a Cleanverse A-Token.
- **Transfer gate (CVI / A-Pass):** an outbound transfer is only constructed after the counterparty wallet's A-Pass identity passes verification — non-compliant transfers are never emitted, instead of being reverted after the fact.

Built solo in the Cleanverse Build: Trusted Assets Hackathon 48h window (Aug 8–9, 2026, UTC). Track: RWA.

## Status

- [x] Sandbox integration verified on **Monad**: `generate_apass` (on-chain tx), `faucet`, `query_deposit_atoken_list` (access_core / apass contract discovery)
- [ ] Core vault flow
- [ ] Web UI
- [ ] Demo video

## License

Apache-2.0
