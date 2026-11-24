# Add seats in BAND Desktop

Recommended **15 seats** in `agents/roster.json`. Add gradually: Coordinator, Architect, API Scout, Harness Engineer, Backend, Frontend, UI Tester, Reviewer, Release Integrator, Reporter first. Add Product, Evaluation, Media, Security for their stage rather than paying 14 models to idle.

For each seat, choose runtime as listed, and use the exact actual model ID available in your installation. Proposed IDs are *preferences*, not claims that the model is enabled under your entitlement. Paste matching `mandates/<seat>.md` into BAND saved instructions where supported. All agents read `AGENTS.md` from the repository.

**Antigravity:** BAND documentation says some runtimes do not support saved instructions. For this seat, include the mandate contents and exact issue instruction in the dispatch message, and require the agent to read `AGENTS.md`; verify the runtime sees that file.

If your OpenCode OpenRouter provider does not expose the proposed model slug, list current models and pick a low-cost tool-calling coding model with stable JSON output. Benchmark 2–3 implementations on a deliberately identical issue with test pass rate, total tokens, latency and PR defects; don't rely solely on price-per-token. For harder architectural and independent review tasks use occasional stronger model escalation, record the cost.

**IMPORTANT:** A seat's runtime is BAND configuration, not automatically installed by putting its mandate in Git. A BAND room transcript demonstrates coordination, but independent Git PR history establishes actual implementation provenance.

V2: create hackathon-judge seat using mandates/hackathon-judge.md; verify actual model IDs and @mention routing for all 15 seats. Use per-task worktrees under sahai-worktrees; shared base is not a concurrent editing directory.
