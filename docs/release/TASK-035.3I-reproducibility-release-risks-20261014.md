# TASK-035.3I — remaining reproducibility and release risks

| Property | Current status | Required evidence/decision |
| --- | --- | --- |
| Source preservation | **LOCAL PASS** for 495 reviewed files; original dirty tree and historical evidence preserved. | Owner selects final candidate and experimental/evidence disposition; archive remains local/ignored. |
| Reproducible source inventory | **PARTIAL**: per-file hashes, inclusion/exclusion and verified extraction exist, but no reviewed commit and multiple sensitive/legacy paths need decisions. | Review/commit exact tree under separate authority, then rehash. |
| Reproducible dependency resolution | **NOT VERIFIED**: broad backend ranges; historical 92-package image lock; frontend lock present but no clean install here. | Lock wheel hashes/indexes and prove fresh resolution; review advisory state. |
| Reproducible image build | **NOT VERIFIED**: no new Docker build; mutable base tags/OS packages and no exported identical images. | Pin inputs, isolated build, image digest/SBOM/scan and API-worker equality. |
| Reproducible model execution | **NOT VERIFIED**: 035.3B recorded local Ollama digest, but full embedding/model bytes and runtime repeat across independent hosts are not established. | Freeze model/cache provenance and repeat qualification. |
| Off-host disaster recovery | **NOT VERIFIED**: local archives/backups/restore evidence only. | Authorized encrypted transfer and independent restore. |
| Current RC RAG safety | **OPEN/FAIL**: independent STAFF unsupported-answer test remains nonresponsive; B19/B21/R18 open. | Safe generic application remediation under separate authority, then targeted and broad new-candidate gates. |
| Active API/worker identity | **UNRESOLVED skew**; accepted V2 API/older worker differ in source and packages. | Approved coordinated same-source candidate qualification/cutover, not this checkpoint. |
| Frontend delivery/security | 035.3H dialog mock gates pass, but live same-source E2E, production API origin/TLS, source-map exposure, broader accessibility, advisory scan and CI frontend jobs remain open. | Owner/security/ops qualification and release-gate evidence. |

No release deferral was approved. Q018 policy authority remains an intentional
corpus conflict. Historical H5.2 accepted V2 98/98 is preserved without
asserting that this current source archive or failed 035.3B candidate is a
new passing RC. TASK-035 remains **IN PROGRESS**, RC **NO-GO**.
