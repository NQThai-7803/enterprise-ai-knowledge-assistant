# TASK-035.3I — source and evidence versioning proposal

No Git write, tag, push, external upload or release approval occurred.

1. On a reviewed `codex/` or owner-selected candidate branch, stage only the
   selected backend/frontend source, migrations, dependency manifests,
   templates, required tests, CI and verification scripts. Review the full
   dirty-tree diff and the JSON inventory against the 035.1/3A baselines.
   Keep historical/experimental material in a separate documented evidence
   commit or access-controlled store as appropriate; do not discard it.
2. Before any commit, resolve the 2E/2F harness disposition, the Gitlink and
   oddly named tracked file, UAT overlay sensitivity, and red safety tests.
   Run secret/private-data review on the exact staged diff. A commit/tree ID
   must identify one source state; no RC tag before qualification and release
   authority approval.
3. Store the accepted H5.2 98/98 record, failed 035.3B permission capture,
   035.3H frontend evidence, source manifests, recovery/restore reports and
   nonsecret build attestations under immutable, access-controlled artifact
   retention. Keep private corpus PDFs, runtime user/grant manifests, DB dumps
   and Redis recovery data outside ordinary source control. Preserve their
   hashes and access controls without publishing document content.
4. Freeze dependency inputs separately: resolved Python 3.12 package/wheel
   hashes and CPU Torch index, `frontend/package-lock.json`, base/OS image
   digests, CI runner/tool versions, API/worker image IDs/exports and an SBOM.
   Record Ollama model content digest, embedding revision/cache checksum and
   nonsecret runtime settings. A model name alone does not pin model bytes.
5. Prove off-host disaster recovery only after an authorized encrypted copy,
   transferred-hash comparison and independent restore of source, data,
   documents and configuration in a disposable environment. The local tar
   and previous local DB restore are insufficient.

The frozen 035.3B images and evidence remain historical **FAIL** artifacts,
not a future baseline. The active API/worker image skew is unresolved.
Versioning should not merge these identities or overwrite their tags.
