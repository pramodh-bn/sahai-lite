# Stage 3 certification status

**Current status: NOT CERTIFIED.**

Per `factory-lite/spec/stage-3.md` ("mock tests separate and insufficient
for stage certification") and `factory-lite/PROTOCOL.md` ("No certification
for missing evidence"), Stage 3 cannot be certified from offline/mock
test results alone, however many of them pass. Passing the cumulative
offline suite (`py -3.12 -m unittest discover -s factory-lite/tests -p
"test_*.py" -v`) demonstrates the *contract and implementation logic* are
sound; it does **not** demonstrate the real Napster companion/avatar,
audio, or handoff integration actually works, because that suite never
makes a live vendor call by design (see `test_s3_live_napster.py`).

Certification requires **all four** of the following gates to be true at
once. Each is explicitly tracked here so "mock passed" can never be
read as "Stage 3 passed":

| Gate | Status | Evidence |
|---|---|---|
| Live authorization | **NOT GRANTED** -- owner has not set `SAH_NAPSTER_LIVE=1` | none |
| Credentials present | **ABSENT** -- no `NAPSTER_API_KEY` (or other required credential env vars) configured for this task | none |
| Account capability confirmed | **UNVERIFIED** -- whether this project's Napster org has an active key, sufficient credits, and the required providers/architectures enabled (e.g. CompanionV2) is undetermined; see `stage3-capability-record.md` | none |
| Redacted real evidence captured | **ABSENT** -- no live probe has ever run, so no evidence file exists | none |

Any future claim that Stage 3 is certified must point to an updated
version of this table with all four rows flipped to met, each with an
evidence path, following a real run of `test_s3_live_napster.py` with the
authorization gate enabled by the owner. Until then: **Stage 3 remains
uncertified**, independent of how many offline tests pass.
