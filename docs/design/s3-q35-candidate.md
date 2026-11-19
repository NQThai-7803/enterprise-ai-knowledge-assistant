# Candidate `s3` + `qwen3.5:4b` (DEC-029)

Measured 2026-11-17. The owner picked `s3` + `qwen3.5:4b` after DEC-028 and set three conditions before the default can change. The default stays `legacy` + `qwen2.5:3b`.

The conditions:

- **(a)** It still wins over three jobs.
- **(b)** The owner reads the UAT errors and accepts them.
- **(c)** It runs on the target hardware.

The measurement plan was written into DEC-029 before the round-c jobs ran.

## (a) Third job (round c)

**Result: (a) holds.** Over the three jobs aA, bA and cA, `s3` + `qwen3.5:4b` still wins against `legacy` + 3B under DEC-026 with DEC-027 extended to three jobs.

Runs (job A of each round):

- aA and bA are the DEC-028 jobs.
- cA: natural 44079801741, rbac 44079841484, relevance 44079881393, false_refusal 44079918719, false_refusal_v2 44079955940, compound 44079993701.

Counts are correct - false refusal - false answer - wrong, per job aA / bA / cA:

| Set | `legacy` + 3B | `s3` + `qwen3.5:4b` |
|---|---|---|
| `natural_dev_v1` (20) | 3-7-1-9 / 3-7-1-9 / 3-7-1-9 | 11-4-1-4 / 9-9-1-1 / 11-5-1-3 |
| rbac (36) | 23-13-0-0 (all three) | 36-0-0-0 (all three) |
| relevance (25) | 18-3-4-0 (all three) | 23-0-2-0 (all three) |
| false_refusal (20) | 13-1-6-0 (all three) | 17-0-3-0 / 18-0-2-0 / 18-0-2-0 |
| false_refusal_v2 (24) | 14-6-4-0 (all three) | 21-0-2-1 / 21-0-2-1 / 22-0-2-0 |
| compound (12) | 4-4-3-1 / 4-5-2-1 / 4-4-3-1 | 9-1-2-0 / 9-2-1-0 / 9-1-2-0 |

The DEC-026 steps, with the three-job rule ("real" = same sign in all three jobs and the smallest difference above the largest between-job change of either side):

1. **Leaks:** 0 on both sides in every job.
2. **False answers + wrong, all six sets:** 15 / 10 / 12 against 28 / 27 / 28. Differences -13, -17, -16, spread 5: **real, fewer**.
3. **False refusals on `natural_dev_v1`:** 4 / 9 / 5 against 7 / 7 / 7. Differences -3, +2, -2: **tie**.
4. **False refusals on the other five sets:** 1 / 2 / 1 against 27 / 28 / 27. Differences -26 in all three: **real, fewer**.

**Variation.** The owner asked about the spread of false refusals (5 against 11 in the first two jobs, all six sets).

- The third job has 6.
- On `natural_dev_v1` alone, the three jobs give 4, 9 and 5; `legacy` gives 7 in all three. Natural false refusals are the one measure that does not separate.

**Latency on the runner (CPU), `natural_dev_v1`:** median 69.1 / 118.6 / 83.3 s per question (`legacy` + 3B: 34.6 / 46.1 / 47.2 s). In job bA, 4 answers took over 180 s; the eval timeout was 600 s, so none failed.

## The text-only copy `qwen3.5-text:4b`

- **The Ollama library has no text-only tag.** Every `qwen3.5:4b` tag lists text and image input (checked on ollama.com, 2026-11-17).
- **The vision encoder is a separate layer of the model.** It is a projector of 675 MB (CLIP, 333.5M parameters).
- **The copy is built without it.** `eval.yml` builds `qwen3.5-text:4b` from the same model layer, template, renderer, parser and parameters, leaving the projector out. It stops if the base model has no projector, or if the copy still reports vision.
- **Measured in round c,** in the same job as `qwen3.5:4b`.

**Result: the copy is a valid deployment option.**

- **Same answers.** In each round-c job, its answer and grounding status equal those of `qwen3.5:4b` on every item: 137 of 137 (20 natural, 117 on the five dev sets). DEC-029 allows a difference up to the between-job change; the difference is zero.
- **Less memory.** From llama.cpp's own breakdown in `ollama.log`, both builds load the same weights: 1296 MiB host + 1698 MiB repacked. `qwen3.5:4b` also loads the projector, which llama.cpp estimates at 868 MiB worst case.
- **Runner peak in the same job,** one line per set: 0.5-0.7 GB lower with the copy.

  | Set | `qwen3.5:4b` | `qwen3.5-text:4b` |
  |---|---|---|
  | natural | 11060 MB | 10375 MB |
  | rbac | 8029 MB | 7362 MB |
  | relevance | 8545 MB | 7898 MB |
  | false_refusal | 7433 MB | 6772 MB |
  | false_refusal_v2 | 8779 MB | 8250 MB |
  | compound | 7423 MB | 6796 MB |

- **Same speed on the CPU:** natural median 83.3 s against 85.0 s.
- **The copy is not in the Ollama library.** A deployment would build it the way `eval.yml` does, or from a Modelfile that leaves out the projector.

## (b) UAT

**Result: waiting for the owner's reading.** The list is in `docs/review/uat-s3-q35-2026-11-17.md`.

**Runs:** UAT Q001-Q100, two rounds, each split into two jobs, each job with its own `legacy` + 3B.

- Round A: 44074751589 (Q001-Q050), 44074786004 (Q051-Q100).
- Round B: 44074821137 (Q001-Q050), 44074856382 (Q051-Q100, second attempt; the first lost its runner, see (c)).

**Grading.** UAT is graded by proxy, as before: answer or refusal, plus the cited document codes, against the manual grade of TASK-035.3B.

- "Wrong" here means a different cited document. The proxy does not read values.
- So the list also has a second part, from a heuristic: proxy-correct answers whose numbers differ from the reference answer.

| | `legacy` + 3B, round A / B | `s3` + `qwen3.5:4b`, round A / B |
|---|---|---|
| correct - false refusal - false answer - wrong (proxy) | 98-1-0-1 / 99-0-0-1 | 67-23-1-9 / 69-22-1-8 |
| by route | deterministic 75 / 76, all correct; LLM 25 / 24 | LLM 100 / 100 |
| wrong with the numbers taken from the cited text (wrong subject) | 0 / 0 | 8 / 7 |
| proxy-correct, numbers differ from the reference (heuristic) | 1 / 1 | 9 / 8 |
| median / p95 / longest latency | 0.9 / 54.6 / 89.0 s; 1.1 / 47.9 / 145.8 s | 76.8 / 122.0 / 131.7 s; 80.8 / 175.3 / 221.1 s |
| runner peak | 6.2 GB | 13.7-14.7 GB |

**The list (19 items) with Claude's first reading,** to be checked by the owner:

- **9 real errors, the same in both rounds:**
  - Q018 answers where the reference refuses.
  - Q019, Q020, Q041, Q048, Q049, Q054, Q077 and Q079 give a wrong or incomplete value.
  - `legacy` + 3B gets all 9 right, 8 of them on the deterministic route. That route was built on UAT itself, which is why UAT is monitoring only (DEC-026).
- **6 of the 9 take the wrong row or column of a table:** Q019, Q048, Q049, Q054, Q077, Q079. That is the same failure as ND-002 (`docs/design/table-chunking.md`).
- **Q043:** right value, but the cited evidence does not support it. It is about carrying leave over up to 03 years; the claim check passed it on the number 03.
- **7 items have the right value from another document** than the manual grade: Q002, Q016, Q017, Q034, Q039, Q040, Q042.
- **2 heuristic false alarms:** Q022, Q060.

**False refusals (23 / 22)** are what drive the gap with `legacy`. They are not on the list, which the owner asked for false answers and wrong values.

## (c) Hardware

### CPU (Actions runner: 4 vCPU, 15.6 GiB, no GPU)

The DEC-029 criterion: no `INFRA_ERROR`, at least 1.5 GB RAM free at the stack's peak, and every answer within the deployment's LLM timeout.

**Result with Ollama's defaults: not met.**

- **One UAT job lost its runner.** uB2 (Q051-Q100, round B, run 44074856382) stopped after 1 h 52 min in the batch step: "The hosted runner lost communication with the server". It left no artifacts.
- **Two halves went below 1.5 GB:** uA2 (the same 50 questions in round A) with 1240 MB free at its lowest, and the second attempt of uB2 with 1249 MB. uA1 had 2130 MB and uB1 2290 MB.
- **`legacy` + 3B in the same jobs:** peak about 6.2 GB, at least 9.8 GB free.

**The cause is llama-server's prompt cache.**

- Ollama 0.40 runs the model in llama-server. llama-server keeps the state of earlier prompts in host RAM, up to 8192 MiB by default ("prompt cache is enabled, size limit: 8192 MiB"). The memory is not freed until the model unloads.
- **Size of one cached prompt** (from the `prompt 0x…` lines):
  - `qwen3.5:4b`: median 222 MiB, at most 280 MiB, at least 101 MiB even for a 25-token prompt. Each context checkpoint also stores the state of the recurrent layers.
  - `qwen2.5:3b`: median 80 MiB, at most 109 MiB.
- From the `cache state` lines in `ollama.log`:

  | Job | Model | Prompts cached | Cache size |
  |---|---|---|---|
  | UAT half, round A or B (50 questions) | `qwen3.5:4b` | 30-35 | 6.6-8.0 GiB |
  | natural cA (20 questions) | `qwen3.5:4b` | 17 | 3.9 GiB |
  | natural aA: `legacy` and `s3` with `qwen3.5:4b`, one server | `qwen3.5:4b` | 26 | 6.5 GiB |
  | natural aA: `legacy` and `s3` with 3B, one server | `qwen2.5:3b` | 29 | 2.1 GiB |

- In rounds a and b, two configurations with `qwen3.5:4b` shared one server, so the cache carried over. That is why the round-a and round-b peaks (13.6 and 14.0 GB on natural) are higher than round c (11.1 GB).
- **This is not specific to the candidate.** With any model, a long-running Ollama 0.40 server grows to the model plus 8 GiB once enough different prompts have passed. A larger model per prompt only gets there sooner. The current default deployment is exposed too.

**The cap.**

- llama-server reads `LLAMA_ARG_CACHE_RAM` (MiB, 0 = off), and Ollama passes its environment through. Checked locally on Ollama 0.40.15: with `LLAMA_ARG_CACHE_RAM=0` the log says "prompt cache is disabled".
- `eval.yml` now has an `ollama_cache_ram` input (`default` keeps Ollama's 8192).
- uB2 was re-run twice:
  - unchanged, as a second attempt;
  - as uB2m with the cap at 2048 MiB, run 44093542862.

| Q051-Q100, `s3` + `qwen3.5:4b` | Cache | Runner peak | Lowest free | Batch time | Median / longest |
|---|---|---|---|---|---|
| uA2 (round A) | default, 7.6 GiB at the end | 14742 MB | 1240 MB | 4084 s | 66.1 / 124.7 s |
| uB2, second attempt (round B) | default, 8.04 GiB (at the limit) | 14733 MB | 1249 MB | 6733 s | 112.8 / 221.1 s |
| uB2m (cap 2048 MiB) | 1.95 GiB | **9152 MB** | **6830 MB** | 4049 s | 66.5 / 122.3 s |

**What the uB2 runs show:**

- **The second attempt of uB2 finished, but it stayed below 1.5 GB free.** Its batch took 65% longer than the same questions in round A, with 4 answers over 180 s.
  - Likely cause: the runner ran short of memory, so the page cache, which holds the model file, was evicted. Not proven.
- **With the cap, the runner kept 6.8 GB free** and the speed of round A.
- **Answers with the cap:** proxy categories equal those of uB2 on 46 of 50 items. Q063 and Q064 moved from correct to false refusal, and Q076 and Q090 the other way, so the totals are equal.
  - Between the two uncapped jobs (uA2 and uB2), all 50 categories were equal.
  - With one capped job, this cannot separate an effect of the cap from job-to-job variation. A capped cache evicts earlier prompts, so the prompt prefix reused for the next request can differ.

**(c) CPU, as fixed in DEC-029: not met with Ollama's defaults.** One runner was lost and two halves stayed below 1.5 GB.

- With the cache capped at 2048 MiB it was met on the one half measured.
- Relying on the cap needs two things:
  - the cap set on the deployment's Ollama host;
  - a measurement of both UAT rounds and the dev sets with the cap, under DEC-027, to check the answers.

**Latency (end to end, CPU):**

- UAT, per question, median / p95 / longest:
  - round A: 76.8 / 122.0 / 131.7 s;
  - round B: 80.8 / 175.3 / 221.1 s; the slow end is the second attempt of uB2.
  - `legacy` + 3B: 0.9 / 54.6 / 89.0 s and 1.1 / 47.9 / 145.8 s, mostly the deterministic route.
- `natural_dev_v1`: see (a).
- The deployment's `LLM_TIMEOUT_SECONDS` is 30 s today. On this CPU it would have to be raised well above that, per call, before the switch; DEC-029 already lists it.

### GPU (the owner's machine: GTX 1650 4 GB, 7.8 GiB RAM, Windows, Ollama 0.40.15)

Measured locally with `ollama ps` and `nvidia-smi`. Ollama was set to `OLLAMA_CONTEXT_LENGTH` 8192 and `OLLAMA_NUM_PARALLEL` 1, as on the runner.

| Model | Placement | `ollama ps` | Layers on GPU | VRAM used (of 4096 MiB) |
|---|---|---|---|---|
| `qwen3.5:4b` | Ollama's own | 3.9 GB, 52% CPU / 48% GPU | 14 of 33 | 2503 MiB |
| `qwen3.5:4b` | forced (`num_gpu` 99) | 3.3 GB, **100% GPU** | 33 of 33 | 3841 MiB |
| `qwen3.5-text:4b` | Ollama's own | 3.6 GB, 36% CPU / 64% GPU | 23 of 33 | 2271 MiB |
| `qwen3.5-text:4b` | forced (`num_gpu` 99) | 3.0 GB, **100% GPU** | 33 of 33 | 2971 MiB |

**Ollama's own placement:**

- **It keeps a reserve.** llama.cpp computes 2903 MiB for the whole model with its 8192-token context, and the card has 3296 MiB free. It still keeps 1693 MiB free with the projector, or 1024 MiB without it, and moves layers to the CPU.
- **So the model never lands fully on the GPU by default.** The first load in the session also saw stale free-memory figures ("unable to refresh free memory"): 11 layers then, 14 after a reload.

**Forced placement:**

- **The whole model fits.** With the projector, it leaves 255 MiB of the card free; without it, 1125 MiB.
- **The app cannot force this itself.** It calls Ollama's `/v1` endpoint, which ignores `options` such as `num_gpu`. Forcing it in a deployment means building a model from a Modelfile with `PARAMETER num_gpu 99`.

**Latency.** The rule was fixed in DEC-029 before measuring:

- **What was replayed:** the s3 LLM calls of ND-001 to ND-010, from the `simple_trace` of CI run 44018356568 (round a, job A). That is 13 calls, because three items had a retry.
- **How:** the same system and user prompts, temperature 0, seed 20261031, `num_ctx` 8192, at most 512 output tokens, no thinking.
- **What it measures:** LLM time per question only. Retrieval, reranking and validation are not included.

| Configuration | Median per question | Range | Generation (tokens/s, median) |
|---|---|---|---|
| `qwen3.5:4b`, Ollama's placement | 29.4 s | 19.5-44.1 s | 4.9 |
| `qwen3.5:4b`, 100% GPU | 20.7 s | 18.6-28.5 s | 33.3 |
| `qwen3.5-text:4b`, Ollama's placement | 24.4 s | 20.7-39.3 s | 10.1 |
| `qwen3.5-text:4b`, 100% GPU | 20.7 s | 18.7-28.6 s | 32.6 |
| Reference: CI runner, CPU, end to end (same 10 questions) | 70.8 s | 67-110 s | |

**What the latency figures show:**

- **On the GPU, most of the time is the prompt** (about 2,300 tokens per call): generation of 30-100 tokens takes 1-3 s.
- **The prompt is re-read in full on every call.** `qwen3.5` has recurrent layers, so llama.cpp re-reads the whole prompt each time ("forcing full prompt re-processing"); the prompt cache does not help. A retry pays the full prompt again.
- **The local machine was under memory pressure:** 7.8 GiB RAM, 1.2 GiB free, with Docker and the protected stacks running. The CPU-side layers of the partial placements pay for that.
- **The prompt cache lives in host RAM on a GPU machine too.** The local server log shows the same "size limit: 8192 MiB". On a 7.8 GiB machine an uncapped cache would run out of memory long before 8 GiB, so a GPU deployment also needs `LLAMA_ARG_CACHE_RAM` (see the CPU section).
