# Stage 09 — run and evidence

The **same root application** is used at each stage, with a Git tag recording the stage snapshot. This differs intentionally from the BAND event's complete copied stage directories, since all product, specs, and harness live in one repo.

1. Check out tag `stage-09-passed` when that tag has been legitimately created. Otherwise use the issue feature branch and clearly label it IN PROGRESS.
2. Install dependencies from the real app manifests in repository root; start service using documented actual command (integration agent must fill this in once stack is chosen).
3. Service must listen on `0.0.0.0:8080` or documented `PORT`.
4. From root run `python -m harness check --repo .` and `python -m harness run --repo . --stage 9 --base-url http://127.0.0.1:8080`.
5. Save CLI output, report JSON, sanitized logs, CI link and reviewer decision under `artifacts/stages/stage-09/`.
6. Never tag the stage until every cumulative test has passed and real-vs-mock behavior is disclosed.

**TODO by release integrator:** replace the abstract service startup instruction with a real pinned Docker build/run command after framework selection. This kit does not contain a runnable Sah application.
