# Model comparison (DEC-028)

Measured 2026-11-17 on `feat/model-compare` (`fa07343`). The candidates, the measurement and the rule were fixed in DEC-028 before any run. The default is unchanged (`legacy`, `qwen2.5:3b`).

Hypothesis (owner): the 3B model is the main bottleneck. With oracle context it is still wrong on about 44% of UAT, the wrong-subject answers of s3 on ND-002/003/011/014/019 are reading errors, and some answers mix in another language.

## Setup

- Models: `qwen2.5:3b` (baseline), `qwen2.5:7b`, `qwen3.5:4b`, `sailor2:8b`; all Q4_K_M, `num_ctx` 8192. The reasons for the choice are in DEC-028.
- Sets: `natural_dev_v1` and the 5 dev sets. UAT is not run.
- Jobs: per set and round, job A = {`legacy`, `s3`} × {3B, 7B, `qwen3.5:4b`} and job B = {`legacy`, `s3`} × {3B, `sailor2:8b`}. Each job has its own `legacy` + 3B. There are two rounds (a, b) on separate jobs, with 1 run per configuration: 24 jobs in all. Every configuration ran with an LLM timeout of 600 s; Ollama kept one model loaded.
- GitHub Actions, 4 vCPU, 15.6 GiB RAM, no GPU, Ollama 0.40.15.
- Counts are correct – false refusal – false answer – wrong (wrong = answered, but wrong value or documents).
- **Leaks: 0 in every cell.** No `INFRA_ERROR`. Every Ollama call returned 200.
- Wrong subject is a heuristic: a wrong answer whose numbers all appear in its cited sources.
- Wrong language: an answered case with a CJK character, or a sentence of at least 5 ASCII words with 2 English stopwords.
  - The six English questions of false refusal v2 (group E) get the CJK test only, since an English answer is right there.
  - That exception was added after the first count. It flagged 4 English answers by `sailor2:8b` to those questions.
- Latency is per question. Runner peak is the whole stack (Postgres, Redis, API, worker, embedding model, Ollama) while the configuration ran.

Runs (round + job: run id):

| Set | aA | aB | bA | bB |
|---|---|---|---|---|
| natural_dev_v1 | 44018356568 | 44018367299 | 44018484184 | 44018494022 |
| RBAC | 44018378115 | 44018388470 | 44018503696 | 44018513010 |
| relevance | 44018398697 | 44018409346 | 44018522456 | 44018533500 |
| false refusal v1 | 44018420576 | 44018431232 | 44018544323 | 44018555000 |
| false refusal v2 | 44018442714 | 44018453027 | 44018564494 | 44018575375 |
| compound | 44018463194 | 44018474068 | 44018585514 | 44018595636 |

## Results per set

Round a / round b in each cell. The two `legacy` + 3B rows of a set (jobs A and B) are separate jobs.

### natural_dev_v1 (20)

| Configuration | Round a | Round b | Near UAT a / b | Rest a / b | Wrong subject | Wrong language | Median s | p95 s | Runner peak GB |
|---|---|---|---|---|---|---|---|---|---|
| legacy, 3B (job A) | 3–7–1–9 | 3–7–1–9 | 1–3–0–3 / 1–2–0–4 | 2–4–1–6 / 2–5–1–5 | 3 / 3 | 1 / 0 | 34.6 / 46.1 | 66.3 / 107.6 | 6.4 / 6.4 |
| s3, 3B (job A) | 4–7–1–8 | 3–8–1–8 | 3–4–0–0 / 3–4–0–0 | 1–3–1–8 / 0–4–1–8 | 4 / 4 | 0 / 0 | 49.4 / 84.0 | 60.5 / 101.3 | 7.8 / 7.8 |
| legacy, 7B | 3–8–0–9 | 3–9–0–8 | 1–2–0–4 / 1–2–0–4 | 2–6–0–5 / 2–7–0–4 | 4 / 4 | 0 / 0 | 75.7 / 118.2 | 122.0 / 206.4 | 9.7 / 9.7 |
| s3, 7B | 7–5–1–7 | 7–6–1–6 | 4–3–0–0 / 3–4–0–0 | 3–2–1–7 / 4–2–1–6 | 2 / 1 | 0 / 0 | 105.5 / 183.3 | 114.1 / 199.0 | 11.9 / 11.9 |
| legacy, qwen3.5:4b | 7–2–1–10 | 7–4–1–8 | 2–1–0–4 / 2–2–0–3 | 5–1–1–6 / 5–2–1–5 | 4 / 4 | 0 / 0 | 38.8 / 69.5 | 104.3 / 207.7 | 9.7 / 10.0 |
| s3, qwen3.5:4b | 11–4–1–4 | 9–9–1–1 | 5–2–0–0 / 4–3–0–0 | 6–2–1–4 / 5–6–1–1 | 1 / 1 | 0 / 0 | 69.1 / 118.6 | 108.0 / 202.0 | 13.6 / 14.0 |
| legacy, 3B (job B) | 3–7–1–9 | 3–7–1–9 | 1–3–0–3 / 1–3–0–3 | 2–4–1–6 / 2–4–1–6 | 3 / 3 | 1 / 1 | 35.3 / 22.0 | 68.0 / 41.1 | 6.4 / 6.4 |
| s3, 3B (job B) | 3–8–1–8 | 3–8–1–8 | 3–4–0–0 / 3–4–0–0 | 0–4–1–8 / 0–4–1–8 | 4 / 4 | 0 / 0 | 50.8 / 29.1 | 63.0 / 38.4 | 7.8 / 7.8 |
| legacy, sailor2:8b | 2–14–1–3 | 2–14–1–3 | 1–5–0–1 / 1–5–0–1 | 1–9–1–2 / 1–9–1–2 | 2 / 2 | 0 / 0 | 158.9 / 100.3 | 265.9 / 169.7 | 10.8 / 10.8 |
| s3, sailor2:8b | 1–18–0–1 | 1–17–0–2 | 0–7–0–0 / 0–7–0–0 | 1–11–0–1 / 1–10–0–2 | 1 / 1 | 0 / 1 | 153.9 / 88.2 | 238.6 / 141.4 | 13.8 / 13.7 |

### RBAC (36 = 18 answerable + 18 negative)

| Configuration | Round a | Round b | Wrong subject | Wrong language | Median s | p95 s | Runner peak GB |
|---|---|---|---|---|---|---|---|
| legacy, 3B (job A) | 23–13–0–0 | 23–13–0–0 | 0 / 0 | 0 / 0 | 25.0 / 35.8 | 47.6 / 80.2 | 6.2 / 6.6 |
| s3, 3B (job A) | 36–0–0–0 | 36–0–0–0 | 0 / 0 | 0 / 0 | 2.1 / 3.1 | 9.0 / 15.2 | 6.1 / 6.8 |
| legacy, 7B | 23–13–0–0 | 23–13–0–0 | 0 / 0 | 0 / 0 | 61.3 / 106.7 | 87.3 / 147.4 | 9.1 / 9.3 |
| s3, 7B | 36–0–0–0 | 36–0–0–0 | 0 / 0 | 0 / 0 | 5.2 / 7.6 | 19.3 / 35.3 | 9.9 / 9.5 |
| legacy, qwen3.5:4b | 22–13–1–0 | 22–13–1–0 | 0 / 0 | 0 / 0 | 70.1 / 124.9 | 96.0 / 166.4 | 9.7 / 9.1 |
| s3, qwen3.5:4b | 36–0–0–0 | 36–0–0–0 | 0 / 0 | 0 / 0 | 18.5 / 31.2 | 20.1 / 33.5 | 9.4 / 9.5 |
| legacy, 3B (job B) | 23–13–0–0 | 23–13–0–0 | 0 / 0 | 0 / 0 | 34.4 / 25.1 | 78.3 / 47.5 | 6.7 / 6.6 |
| s3, 3B (job B) | 36–0–0–0 | 36–0–0–0 | 0 / 0 | 0 / 0 | 2.9 / 2.1 | 14.4 / 9.0 | 6.2 / 6.4 |
| legacy, sailor2:8b | 23–13–0–0 | 23–13–0–0 | 0 / 0 | 0 / 0 | 187.0 / 122.0 | 234.0 / 157.6 | 9.8 / 9.7 |
| s3, sailor2:8b | 35–0–1–0 | 35–0–1–0 | 0 / 0 | 0 / 0 | 10.8 / 8.2 | 35.4 / 24.1 | 10.2 / 10.8 |

### relevance (25)

| Configuration | Round a | Round b | Wrong subject | Wrong language | Median s | p95 s | Runner peak GB |
|---|---|---|---|---|---|---|---|
| legacy, 3B (job A) | 18–3–4–0 | 18–3–4–0 | 0 / 0 | 0 / 0 | 19.6 / 19.9 | 54.6 / 55.9 | 5.9 / 5.9 |
| s3, 3B (job A) | 20–0–4–1 | 21–0–4–0 | 0 / 0 | 0 / 0 | 10.1 / 10.3 | 20.6 / 20.9 | 6.1 / 6.1 |
| legacy, 7B | 17–3–4–1 | 17–3–4–1 | 0 / 0 | 0 / 0 | 42.9 / 42.6 | 87.6 / 86.3 | 9.0 / 8.9 |
| s3, 7B | 20–0–5–0 | 21–0–4–0 | 0 / 0 | 0 / 0 | 21.6 / 21.5 | 38.8 / 38.5 | 9.4 / 9.3 |
| legacy, qwen3.5:4b | 18–3–4–0 | 18–3–4–0 | 0 / 0 | 0 / 0 | 32.2 / 32.1 | 100.6 / 100.2 | 8.6 / 8.5 |
| s3, qwen3.5:4b | 23–0–2–0 | 23–0–2–0 | 0 / 0 | 0 / 0 | 28.7 / 28.3 | 38.9 / 39.5 | 9.4 / 9.3 |
| legacy, 3B (job B) | 18–3–4–0 | 18–3–4–0 | 0 / 0 | 0 / 0 | 14.8 / 15.4 | 40.6 / 40.5 | 6.1 / 6.1 |
| s3, 3B (job B) | 20–0–5–0 | 20–0–5–0 | 0 / 0 | 0 / 0 | 7.5 / 8.1 | 13.0 / 12.4 | 6.3 / 6.3 |
| legacy, sailor2:8b | 12–9–4–0 | 12–9–4–0 | 0 / 0 | 0 / 0 | 117.0 / 116.6 | 159.6 / 162.1 | 10.0 / 10.1 |
| s3, sailor2:8b | 20–0–5–0 | 21–0–4–0 | 0 / 0 | 0 / 0 | 18.8 / 23.9 | 45.2 / 61.2 | 10.6 / 10.6 |

### false refusal v1 (20)

| Configuration | Round a | Round b | Wrong subject | Wrong language | Median s | p95 s | Runner peak GB |
|---|---|---|---|---|---|---|---|
| legacy, 3B (job A) | 13–1–6–0 | 13–1–6–0 | 0 / 0 | 0 / 0 | 30.7 / 15.9 | 66.9 / 35.2 | 5.8 / 6.3 |
| s3, 3B (job A) | 14–2–4–0 | 15–2–3–0 | 0 / 0 | 0 / 0 | 3.6 / 3.9 | 21.5 / 13.2 | 5.9 / 6.4 |
| legacy, 7B | 14–2–4–0 | 14–2–4–0 | 0 / 0 | 0 / 0 | 70.2 / 31.5 | 139.3 / 78.4 | 8.8 / 8.9 |
| s3, 7B | 18–0–2–0 | 18–0–2–0 | 0 / 0 | 0 / 0 | 6.8 / 7.9 | 49.6 / 26.9 | 9.0 / 9.1 |
| legacy, qwen3.5:4b | 14–1–4–1 | 15–1–3–1 | 0 / 0 | 0 / 0 | 40.9 / 22.4 | 145.3 / 93.1 | 8.1 / 8.8 |
| s3, qwen3.5:4b | 17–0–3–0 | 18–0–2–0 | 0 / 0 | 0 / 0 | 41.0 / 18.1 | 42.4 / 21.0 | 8.6 / 9.3 |
| legacy, 3B (job B) | 13–1–6–0 | 13–1–6–0 | 0 / 0 | 0 / 0 | 15.6 / 19.0 | 37.3 / 41.6 | 6.3 / 5.8 |
| s3, 3B (job B) | 15–2–3–0 | 14–2–4–0 | 0 / 0 | 0 / 0 | 4.1 / 2.7 | 12.8 / 13.7 | 6.4 / 6.0 |
| legacy, sailor2:8b | 13–7–0–0 | 13–7–0–0 | 0 / 0 | 0 / 0 | 113.7 / 110.8 | 193.1 / 160.7 | 9.9 / 9.6 |
| s3, sailor2:8b | 17–1–2–0 | 17–1–2–0 | 0 / 0 | 0 / 0 | 18.5 / 9.1 | 33.9 / 33.2 | 10.1 / 9.9 |

### false refusal v2 (24)

| Configuration | Round a | Round b | Wrong subject | Wrong language | Median s | p95 s | Runner peak GB |
|---|---|---|---|---|---|---|---|
| legacy, 3B (job A) | 14–6–4–0 | 14–6–4–0 | 0 / 0 | 0 / 0 | 26.6 / 53.3 | 45.8 / 85.8 | 6.7 / 6.4 |
| s3, 3B (job A) | 20–2–2–0 | 21–1–2–0 | 0 / 0 | 0 / 0 | 11.5 / 27.9 | 16.9 / 39.2 | 6.9 / 6.7 |
| legacy, 7B | 16–7–1–0 | 15–7–2–0 | 0 / 0 | 0 / 0 | 55.0 / 111.6 | 79.8 / 193.8 | 9.8 / 9.8 |
| s3, 7B | 20–2–2–0 | 22–1–1–0 | 0 / 0 | 0 / 0 | 23.1 / 64.1 | 39.2 / 97.7 | 10.2 / 10.2 |
| legacy, qwen3.5:4b | 13–7–4–0 | 13–7–4–0 | 0 / 0 | 0 / 0 | 49.5 / 104.2 | 83.3 / 173.4 | 10.4 / 9.7 |
| s3, qwen3.5:4b | 21–0–2–1 | 21–0–2–1 | 1 / 1 | 0 / 0 | 21.0 / 52.0 | 31.8 / 60.5 | 12.0 / 11.5 |
| legacy, 3B (job B) | 14–6–4–0 | 14–6–4–0 | 0 / 0 | 0 / 0 | 21.1 / 32.7 | 33.2 / 51.5 | 6.3 / 6.5 |
| s3, 3B (job B) | 20–1–3–0 | 21–0–3–0 | 0 / 0 | 0 / 0 | 9.3 / 13.3 | 13.2 / 23.2 | 6.7 / 6.8 |
| legacy, sailor2:8b | 11–11–2–0 | 11–11–2–0 | 0 / 0 | 0 / 0 | 71.2 / 109.6 | 110.7 / 174.8 | 10.8 / 10.8 |
| s3, sailor2:8b | 19–0–5–0 | 19–0–5–0 | 0 / 0 | 0 / 0 | 25.8 / 32.9 | 47.0 / 73.9 | 11.4 / 11.5 |

### compound (12)

| Configuration | Round a | Round b | Wrong subject | Wrong language | Median s | p95 s | Runner peak GB |
|---|---|---|---|---|---|---|---|
| legacy, 3B (job A) | 4–4–3–1 | 4–5–2–1 | 1 / 1 | 0 / 0 | 59.4 / 32.5 | 94.6 / 57.4 | 6.4 / 6.7 |
| s3, 3B (job A) | 6–4–2–0 | 6–4–2–0 | 0 / 0 | 1 / 0 | 17.4 / 7.5 | 22.6 / 15.0 | 6.6 / 6.9 |
| legacy, 7B | 4–5–3–0 | 4–5–3–0 | 0 / 0 | 0 / 0 | 145.6 / 72.0 | 163.2 / 78.7 | 9.9 / 10.1 |
| s3, 7B | 9–0–3–0 | 10–1–1–0 | 0 / 0 | 0 / 0 | 31.5 / 14.3 | 60.9 / 29.9 | 10.2 / 10.3 |
| legacy, qwen3.5:4b | 4–5–2–1 | 4–5–2–1 | 1 / 1 | 0 / 0 | 95.2 / 58.0 | 126.9 / 67.7 | 11.5 / 12.1 |
| s3, qwen3.5:4b | 9–1–2–0 | 9–2–1–0 | 0 / 0 | 0 / 0 | 44.8 / 20.3 | 94.0 / 40.8 | 12.0 / 12.6 |
| legacy, 3B (job B) | 4–4–3–1 | 4–5–2–1 | 1 / 1 | 0 / 0 | 59.6 / 22.7 | 94.6 / 35.9 | 6.4 / 6.5 |
| s3, 3B (job B) | 6–4–2–0 | 7–3–2–0 | 0 / 0 | 1 / 2 | 11.1 / 6.8 | 22.7 / 7.4 | 6.6 / 6.6 |
| legacy, sailor2:8b | 4–3–4–1 | 3–3–5–1 | 1 / 1 | 0 / 0 | 201.1 / 73.0 | 248.1 / 90.3 | 10.6 / 10.5 |
| s3, sailor2:8b | 9–0–3–0 | 10–1–1–0 | 0 / 0 | 0 / 0 | 36.4 / 18.6 | 80.2 / 27.4 | 11.0 / 10.9 |

### Totals

| Configuration | 5 dev sets a | 5 dev sets b | 6 sets a | 6 sets b |
|---|---|---|---|---|
| legacy, 3B (job A) | 72–27–17–1 | 72–28–16–1 | 75–34–18–10 | 75–35–17–10 |
| s3, 3B (job A) | 96–8–12–1 | 99–7–11–0 | 100–15–13–9 | 102–15–12–8 |
| legacy, 7B | 74–30–12–1 | 73–30–13–1 | 77–38–12–10 | 76–39–13–9 |
| s3, 7B | 103–2–12–0 | 107–2–8–0 | 110–7–13–7 | 114–8–9–6 |
| legacy, qwen3.5:4b | 71–29–15–2 | 72–29–14–2 | 78–31–16–12 | 79–33–15–10 |
| s3, qwen3.5:4b | 106–1–9–1 | 107–2–7–1 | 117–5–10–5 | 116–11–8–2 |
| legacy, 3B (job B) | 72–27–17–1 | 72–28–16–1 | 75–34–18–10 | 75–35–17–10 |
| s3, 3B (job B) | 97–7–13–0 | 98–5–14–0 | 100–15–14–8 | 101–13–15–8 |
| legacy, sailor2:8b | 63–43–10–1 | 62–43–11–1 | 65–57–11–4 | 64–57–12–4 |
| s3, sailor2:8b | 100–1–16–0 | 102–2–13–0 | 101–19–16–1 | 103–19–13–2 |

## DEC-026/027: each combination against `legacy` + 3B of its own job

Each cell gives the two rounds (a / b) of the combination against those of `legacy` + 3B. "real" means the same sign in both rounds, with the smaller difference above the larger between-round change of either side (DEC-027). FA + W is false answers + wrong over the 6 sets.

| Combination | Leaks | FA + W, 6 sets | False refusals, natural_dev_v1 | False refusals, 5 dev sets | Verdict |
|---|---|---|---|---|---|
| s3, 3B (job A) | 0 | 22/20 vs 28/27, lower (real) | 7/8 vs 7/7, tie | 8/7 vs 27/28, lower (real) | wins in job A |
| s3, 3B (job B) | 0 | 22/23 vs 28/27, lower (real) | 8/8 vs 7/7, **+1 (real)** | 7/5 vs 27/28, lower (real) | loses on natural in job B; with PR #40 (+1 real in both jobs) **not a win**, as decided |
| legacy, 7B | 0 | 22/22 vs 28/27, lower (real) | 8/9 vs 7/7, tie | 30/30 vs 27/28, **higher (real)** | **does not win**: fewer wrong answers become refusals |
| s3, 7B | 0 | 20/15 vs 28/27, lower (real) | 5/6 vs 7/7, tie | 2/2 vs 27/28, lower (real) | **wins** |
| legacy, qwen3.5:4b | 0 | 28/25 vs 28/27, tie (not above) | 2/4 vs 7/7, **lower (real)** | 29/29 vs 27/28, tie | **wins** (on natural refusals) |
| s3, qwen3.5:4b | 0 | 15/10 vs 28/27, lower (real) | 4/9 vs 7/7, tie | 1/2 vs 27/28, lower (real) | **wins** |
| legacy, sailor2:8b | 0 | 15/16 vs 28/27, lower (real) | 14/14 vs 7/7, **+7 (real)** | 43/43 vs 27/28, higher (real) | **does not win** |
| s3, sailor2:8b | 0 | 17/15 vs 28/27, lower (real) | 18/17 vs 7/7, **+11/+10 (real)** | 1/2 vs 27/28, lower (real) | **does not win** |

The winners compared with each other (job A, both rounds):

- **`s3` + `qwen3.5:4b` against `s3` + 7B: a tie on every count.**
  - natural correct: 11/9 vs 7/7.
  - natural false refusals: 4/9 vs 5/6.
  - FA + W over 6 sets: 15/10 vs 20/15.
  - 5-set false refusals: 1/2 vs 2/2.
- Both beat `legacy` + `qwen3.5:4b`, with fewer false answers + wrong (15/10 and 20/15 vs 28/25) and fewer 5-set false refusals (1/2 and 2/2 vs 29/29).
- Both beat `s3` + 3B of the same job:
  - natural correct: 11/9 and 7/7 vs 4/3, real;
  - 5-set false refusals: 1/2 and 2/2 vs 8/7, real;
  - `qwen3.5:4b` also has fewer false answers + wrong: 15/10 vs 22/20, real.

Over the 6 sets (a / b):

| Combination | Correct | False refusals | FA + W |
|---|---|---|---|
| `legacy` + 3B | 75 / 75 | 34 / 35 | 28 / 27 |
| `s3` + 3B | 100 / 102 | 15 / 15 | 22 / 20 |
| `s3` + 7B | 110 / 114 | 7 / 8 | 20 / 15 |
| `s3` + `qwen3.5:4b` | 117 / 116 | 5 / 11 | 15 / 10 |

## The five wrong-subject items of s3

OK correct, FR false refusal, FA false answer (over-claim on a limited item), W wrong. 3B has 4 rounds (two jobs), the others 2.

| Item (gold) | legacy 3B | s3 3B | legacy 7B | s3 7B | legacy q3.5 | s3 q3.5 | legacy sailor2 | s3 sailor2 |
|---|---|---|---|---|---|---|---|---|
| ND-002 (limited: the bonus goes to the referrer) | FA ×4 | FA ×4 | FR ×2 | FA ×2 | FA ×2 | FA ×2 | FA ×2 | FR ×2 |
| ND-003 (five core values) | FR ×4 | W ×4 | W ×2 | W ×2 | W ×2 | FR ×2 | FR ×2 | FR, W |
| ND-011 (`compliance@`) | W ×3, FR | W ×4 | FR ×2 | **OK ×2** | FR ×2 | **OK ×2** | FR ×2 | FR ×2 |
| ND-014 (limited: number of team-building events not stated) | FR ×4 | W ×4 | FR ×2 | W ×2 | W ×2 | W ×2 | FR ×2 | FR ×2 |
| ND-019 (steps when off sick) | W ×4 | W ×4 | W ×2 | W ×2 | W ×2 | **OK ×2** | W ×2 | **OK ×2** |

**Still wrong with every model: ND-002, ND-003 and ND-014.**

- ND-002: every model that answers still says the candidate gets the Employee Referral Bonus (3 to 15 million). 7B in `legacy` and sailor2 in `s3` refuse instead.
- ND-003:
  - 7B in `legacy` lists values 01 to 04 verbatim and leaves out the fifth ("học hỏi liên tục"). The excerpt of its own page-4 citation contains it; whether the prompt held it was not checked. `legacy` + `qwen3.5:4b` stops at the same four.
  - s3 + 3B describes the company's positioning, not its values. s3 + `sailor2:8b` (round b) invents three values.
- ND-014: every answering model gives the company trip's "01 lần/năm" as the team-building frequency.

**Fixed by a stronger model in `s3`:**

- ND-011 with 7B and `qwen3.5:4b`: they name `compliance@`, where 3B named `soc@`.
- ND-019 with `qwen3.5:4b` and `sailor2:8b`: they give the manager notice, the HRM sick-leave entry and the minimal handover, where 3B gave the BHXH child-care rule.

## Hardware and latency

Model memory comes from Ollama's own breakdown at load: weights, KV cache for 8192 tokens, and compute buffer. On a GPU with full offload, the VRAM need is about that total plus the runtime's overhead (estimated, not measured; no GPU was used).

| Model | Weights on disk | Model memory (weights + KV + compute) | Runner peak, whole stack: legacy / s3 | Latency against 3B, median of per-set ratios: legacy / s3 | VRAM estimate |
|---|---|---|---|---|---|
| `qwen2.5:3b` | 1.79 GiB | 2.3 GiB (1.8 + 0.28 + 0.18) | 5.8–6.7 / 5.9–7.8 GB | 1 / 1 | about 3 GB |
| `qwen2.5:7b` | 4.36 GiB | 5.1 GiB (4.4 + 0.44 + 0.30) | 8.8–10.1 / 9.0–11.9 GB | ×2.2 / ×2.1 | about 6 GB |
| `qwen3.5:4b` | 2.46 GiB | 2.9 GiB + vision encoder up to 0.85 GiB = 3.8 GiB | 8.1–12.1 / 8.6–14.0 GB | ×1.6 / ×2.7 | about 4.5 GB |
| `sailor2:8b` | 4.88 GiB | 5.7 GiB (4.9 + 0.50 + 0.30) | 9.6–10.8 / 9.9–13.8 GB | ×4.7 / ×3.0 | about 6.5 GB |

- Median latency per question on this runner, over sets and rounds:
  - `legacy` + 3B: 15–60 s;
  - `s3` + 3B: 2–84 s;
  - `s3` + 7B: 5–183 s;
  - `s3` + `qwen3.5:4b`: 18–119 s.
- The lowest free memory was 1.9 GB (`s3` + `qwen3.5:4b`) and 2.2 GB (`s3` + `sailor2:8b`) of 15.6 GiB, so a 16 GB CPU machine is at its limit with those.
- The runner peak is higher in `s3` than in `legacy`, by more for larger models. On natural_dev_v1 round a, the median used memory was:

  | Model | `legacy` | `s3` |
  |---|---|---|
  | 3B | 6.0 GB | 7.1 GB |
  | 7B | 9.1 GB | 10.8 GB |
  | `qwen3.5:4b` | 8.2 GB | 11.8 GB |

  The cause was not established.
- `qwen3.5:4b` loads its vision encoder although the app sends text only.
- `qwen3.5:4b` has recurrent (hybrid) layers, so llama.cpp re-processes the whole prompt on every call ("forcing full prompt re-processing"); the prompt cache does not help it.
- Answers over 180 s: 3B 0 of 1,096; 7B 23 of 548; `qwen3.5:4b` 9 of 548; `sailor2:8b` 51 of 548. The old 180 s timeout would have cut those off.

## Other findings

- **`qwen3.5:4b` is less stable between rounds than the others.** In `s3` it had 4 and 9 false refusals on natural_dev_v1 (ND-005, 007, 015, 017, 018 flipped).
  - These were not timeouts. The drafts were reworded, and the s3 validator rejected them on both attempts:
    - `_numbers_are_contradicted` on "Tháng 01 - 02 của năm" (ND-018);
    - `_polarity_is_contradicted` (ND-015, ND-017);
    - `_yes_no_evidence_has_required_anchor` (ND-007);
    - a missing citation (ND-005).
  - Where the model reads better, the validator becomes the limit.
- **RBD-03 (an RBAC negative), answered by `legacy` + `qwen3.5:4b` and `s3` + `sailor2:8b` in both rounds.**
  - They cite only RBAC-ORG-001, which the staff account may read: "báo cho lễ tân tầng 1".
  - The manager-only value is not in the answer, and no restricted document is cited. So it counts as a false answer, not a leak.
- **Wrong language** (English absence sentence or English line in a Vietnamese answer):
  - 3B: `legacy` ND-011, three times; `s3` compound CP1-P01/P06, four times;
  - `sailor2:8b` (`s3`): once, ND-017;
  - 7B and `qwen3.5:4b`: never.
- **`sailor2:8b` refuses far more in `legacy`:** 14 natural false refusals against 7, and 43 against 27 on the 5 sets. It is also the slowest model.
- **The qwen2.5:3b licence (Qwen Research) does not allow commercial use without a licence from Alibaba Cloud.** The other three are Apache 2.0.

## Oracle context with the best model (step 4)

- **Model: `qwen3.5:4b`.** It was picked on its point estimate: it had the most correct answers in total. Under DEC-027 it ties with `s3` + 7B.
- **Jobs:** one job per dev set, one run, configurations {`legacy`, `s3`} × {3B, `qwen3.5:4b`} with `EVAL_ABLATION=oracle`. They ran on the same code and runner as above.
  - Runs: RBAC 44049689550, relevance 44049717283, false refusal v1 44049747156, false refusal v2 44049774992, compound 44049804057.
  - natural_dev_v1 has no oracle map, and UAT was not run (owner's instruction), so neither is covered.
  - `EVAL_SIMPLE_TRACE` (eval-only trace) was left out to keep the configuration string within the workflow's concurrency-group limit.
- **What the oracle changes:** it puts the gold chunks of an answerable item in the prompt. Items to refuse run unchanged (`simple-answer-mode.md`), so it can only move false refusals and wrong values, not false answers.
- **Leaks: 0** in every cell.

Correct – false refusal – false answer – wrong:

| Set | `legacy` + 3B | `s3` + 3B | `legacy` + `qwen3.5:4b` | `s3` + `qwen3.5:4b` |
|---|---|---|---|---|
| RBAC (36) | 26–10–0–0 | 34–1–0–1 | 25–10–1–0 | 36–0–0–0 |
| relevance (25) | 19–2–4–0 | 19–0–5–1 | 20–2–3–0 | 22–0–2–1 |
| false refusal v1 (20) | 13–2–5–0 | 13–3–4–0 | 15–0–4–1 | 17–0–3–0 |
| false refusal v2 (24) | 15–5–4–0 | 20–2–2–0 | 16–5–3–0 | 20–1–3–0 |
| compound (12) | 4–3–4–1 | 5–5–2–0 | 4–6–2–0 | 9–2–1–0 |
| **Oracle, 5 sets (117)** | **77–22–17–1** | **91–11–13–2** | **80–23–13–1** | **104–3–9–1** |
| Real retrieval, job A, round a / b | 72–27–17–1 / 72–28–16–1 | 96–8–12–1 / 99–7–11–0 | 71–29–15–2 / 72–29–14–2 | 106–1–9–1 / 107–2–7–1 |
| Median s per set (oracle) | 15–50 | 3–12 | 36–70 | 12–27 |
| Runner peak GB (oracle) | 6.5 | 6.8 | 9.9 | 11.3 |

- **With `s3`, gold context does not raise the result on these sets.**
  - `s3` + `qwen3.5:4b` gets 104 correct with gold context, against 106 / 107 with real retrieval.
  - `s3` + 3B gets 91, against 96 / 99.
  - These are single runs, so the small negative gaps are within run-to-run change. The ceiling of `s3` + `qwen3.5:4b` on the 5 dev sets is about 104–107 of 117, and real retrieval already reaches it.
- **With `legacy`, gold context cuts false refusals**, but `legacy` still refuses 22–23 items it has the gold for, with either model:
  - 3B: 27–28 → 22;
  - `qwen3.5:4b`: 29 → 23.

  So those refusals come from the `legacy` answer path, not from the model or retrieval.
- **What is left for `s3` + `qwen3.5:4b` is mostly false answers on items to refuse, which the oracle does not touch.**
  - Under the oracle it gets 13 items wrong: 9 false answers, 1 wrong, 3 false refusals.
  - 7 of them are also wrong in both real-retrieval rounds:
    - six false answers: REL-103, REL-203, FR-N07, FR-A07, FR2-C05, CP1-R02;
    - one false refusal: CP1-P04.
  - Four flip between rounds: CP1-A02, FR-A09, FR2-L05, FR2-L06.
  - Two are wrong only under the oracle: FR2-F03 (false refusal), REL-106 (wrong).
- **This does not measure the ceiling where retrieval is hard** (natural_dev_v1, UAT). The 44% UAT failure with gold context in the hypothesis is a 3B figure and was not re-measured with the new model.

## Limits

- The prompts and the thresholds (s3's e5 relevance check 0.78, legacy's responsiveness check 0.80) were calibrated on 3B. A larger model can lose answers to a threshold or to the claim validator, not to its reading; `qwen3.5:4b` round b shows this.
- Two rounds, one run each, and small sets: natural_dev_v1 has 20 items. A tie under DEC-027 is not evidence of equality.
- Hardware figures are CPU-only on a shared runner, so latency changes up to 2× between rounds on the same configuration. VRAM is estimated, not measured.
- Runner peak memory counts the whole stack. The model figures come from Ollama's log.
- Wrong subject is a heuristic count. The five items were read by hand.
