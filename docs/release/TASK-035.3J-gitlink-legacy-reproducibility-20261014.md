# TASK-035.3J — Gitlink and legacy-source reproducibility

`vite-monorepo` is a tracked Gitlink (mode 160000) at commit
`3becadbd1d46a68a61a173731a3c7b946fec024f`. The nested checkout has
its own `.git` directory, is locally clean, and contains that commit object.
It has **no configured origin**. The parent has **no `.gitmodules`** mapping;
the parent object database does not contain the nested commit. Thus the
local checkout is inspectable, but a fresh clone of the parent has no
documented URL from which to populate the Gitlink. Fresh-clone recovery is
**NOT VERIFIED and presently unsupported by recorded configuration**.
No parent Docker/CI/current frontend build reference to `vite-monorepo`
was found. Do not delete the Gitlink, flatten the embedded repository, or
infer the nested project is disposable; owner must decide whether to retain
with an authorized fetch/provenance path or preserve separately.

Other legacy/review-required material:

| Path | Actual observation and role | Build/test/history/sensitivity | Decision |
| --- | --- | --- | --- |
| `tore package.json package-lock.json` | Tracked 1,829-byte file, SHA-256 `91e1901b44c7769b5bba29d2b5346a8bda5fe463309571397bb3bea82bb6ea56`; contents are a Git diff fragment touching frontend package/Vite and a stitch reference, not JSON manifest data. | Not referenced by current build/CI. Historical editing provenance possible; no secret seen in inspected fragment. | REVIEW_REQUIRED before any future removal or separate archive. |
| `files-for-chat/**`, `frontend/files-for-chat/**` | Tracked copied specifications/code excerpts; reference search found no active Docker/CI import. | Not required for current build; may preserve prior context and potentially copied source/document content. | REVIEW_REQUIRED; preserve history and privacy-review before publication. |
| `frontend-stitch-reference/**` | Tracked design HTML/description and PNG screenshot; no current build/CI reference found. | Not needed for current build; design provenance/licensing/privacy not established. | REVIEW_REQUIRED; no deletion or publication assertion. |
| `frontend/.agents/**`, `frontend/skills-lock.json` | Tracked local design-agent guidance/lock, outside frontend production build imports. | Possible tool provenance, not verified runtime input. | REVIEW_REQUIRED with frontend owner. |
| `enterprise_ai_md_updates_2026-08-19_v6.zip`, `Modelfile.qwen2.5-7b-8k`, `README_UPDATE.txt` | Tracked historical package/model/instruction material. Active accepted model is `qwen2.5:3b`, not the 7B Modelfile. | No current build dependency established; binary archive may contain material requiring privacy review. | REVIEW_REQUIRED; do not erase historical source. |
| `scripts/uat/**`, `compose.uat-corpus-v2*.yaml` | Untracked corpus bootstrap/backup/recovery and isolated-stack configuration; separate from generic Compose build paths. | Useful for historical UAT reproduction, but operations may handle private corpus/credentials and are not public-source approved. | REVIEW_REQUIRED for controlled tooling/evidence storage. |

These tracked legacy paths remain in Git history even if a future `git add`
manifest omits them. A clean source tree or fresh-clone claim cannot be made
until the Gitlink and legacy disposition is explicitly approved and tested.
