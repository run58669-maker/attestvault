# 提交邮件草稿(发送人:小Q 亲手按键;收件:isaac@cleanverse.com)

**Subject:** AttestVault — RWA track submission (Application No. INC20260731905294)

---

Dear Cleanverse team,

Please find our submission for the Trusted Assets Hackathon, RWA track.

**Project:** AttestVault — a compliance-gated vault for real-world assets. Deposits only accept registered Cleanverse A-Tokens (CVA); outbound transfers are constructed only after the counterparty passes A-Pass verification (CVI) — non-compliant transfers are never emitted, fail closed. Signature demo: an on-chain A-Pass freeze flips the same transfer from ALLOW to DENY within seconds.

- **Public GitHub repo (Apache-2.0, all commits inside the hacking window):**
  https://github.com/run58669-maker/attestvault
- **Demo video:** ⟪VIDEO_LINK_PENDING⟫
- **One-page summary:** ONE_PAGER.md in the repo root (problem / solution / CVI·CVA integration points / deployed chain), also attached as PDF.
- **Deployment:** runs against the Cleanverse sandbox rails on **Monad** (aUSDC A-Token, access_core, A-Pass contracts as discovered via `query_deposit_atoken_list`). All A-Pass mints, freezes and reinstates in the demo are real Monad transactions; `demo.py` in the repo reproduces the full flow in ~60 seconds.

Team: AttestVault (solo builder, registered as Wei Fang, run58669@gmail.com).

Thank you — we enjoyed building on the rails. The freeze-flip is best enjoyed live.

Best regards,
Wei Fang / AttestVault

---

## 发送前核对清单(小克执行,全绿才许呈给小Q)
- [ ] 视频链接已填且匿名可看(oembed 验证)
- [ ] repo 匿名 200 + LICENSE 在 + 无凭证(最后一次密钥扫描)
- [ ] ONE_PAGER 导出 PDF 并附上
- [ ] demo.py 在干净环境跑通一遍(最终回归)
- [ ] 一封邮件一支队伍 ✓(规则:one email per team)
- [ ] 小Q 终审视频 + 亲手按发送
