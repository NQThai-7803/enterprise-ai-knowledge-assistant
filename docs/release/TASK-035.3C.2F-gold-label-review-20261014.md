# TASK-035.3C.2F — gold-label quality review

Date: 2026-10-14. Historical 2E manifest, A–O synthetic contract, and their labels were read, **not changed**. New 2F case labels/rationales remain as frozen in the [manifest](../../artifacts/task-035-3c2f-20261014/synthetic-manifest.json). This is an engineering review by one author, not independent human adjudication.

## Historical labels and proposed clarifications (not applied)

The prior 2E 36-case set explicitly labeled proposed-answer decisions, not what a complete production assistant should write. No clear historical `ACCEPT` ↔ `REJECT` reversal was established from its displayed synthetic evidence. Several labels need a richer annotation contract before serving as release truth:

| Cases | Retained historical label | Ambiguity or proposed *separate* annotation |
| --- | --- | --- |
| D11, H22 | REJECT | The asserted answer is unsupported **for the scoped requester** because only restricted text provides it. Annotate authorization failure separately from semantic falsity; do not expose restricted text to an evaluator. |
| H03, H15, H23 | REJECT | These proposed factual answers are unsupported (unspecified duration, absent approver, injection-as-fact). A safe final response might explain missing evidence or abstain; `REJECT` here does not prescribe user-facing wording. |
| D12, H07, H16 | UNCERTAIN | This means unresolved **source authority** for the requested policy answer. The proposed unqualified yes/no assertion must not be accepted. Store `conflict=true` separately, rather than treating UNCERTAIN as a weaker form of support. No supersession metadata is present. |
| H06, H13, D04 | REJECT | Missing a mandatory condition makes a permissive answer materially incomplete. Distinguish a non-exhaustive overview from an answer to “under what conditions/what must be done”; these questions request all stated prerequisites. |
| H08 | ACCEPT | A correct “No” plus required sign-off answers a false-permission premise; exact lexical similarity is not needed. |
| H17, H19, H24, D05, D09 | ACCEPT | English/Vietnamese role/action paraphrases are acceptable only if the actor and action relation remain the same; multiple valid phrasings exist. Translation equivalence should be independently bilingual-reviewed. |
| H04, H14, H21 | ACCEPT | Each cited source supplies a different mandatory part. A future gold record should map obligations to specific source IDs and test citation materiality for each part, not only answer correctness. |

The A–O contract contains the same design tensions: E–G/H/I are intended valid paraphrase, multi-document, and false-premise positives; C/D/J/L/M/N are intended nonresponsive, reversed, wrong-value, or incomplete negatives. Its 8/15 failing status is a **verified code behavior** at the prior checkpoint, not evidence that every gold nuance has been independently adjudicated. The original STAFF travel-approval failure is a separate captured runtime defect, not part of this synthetic gold.

## New 2F labels and limitations

Every new case records question, authorized evidence, proposed answer, explicit required obligations, expected decision, materiality, and rationale. `restricted_evidence` is synthetic and never passed to the model/validator. The 24 final-test cases were created and frozen before the prototype ran. No result-driven edits were made to their labels or wording.

New labels deliberately distinguish `REJECT` for wrong propositions (F-T02/03/04/06/10/11/13/14/19/21/23), missing authorized support (F-T18), and `UNCERTAIN` for genuine unordered policy conflict (F-T07/15). The two conflicts' unqualified proposed answers are unsafe to accept even though one visible source supports each. Positive examples allow concise conditional wording and English/Vietnamese/mixed paraphrases (F-T01/05/08/09/12/16/17/20/22/24); exact string overlap is not required. F-T05/06 and F-T12/13 are paired positives/negative omissions from the same synthetic clauses; useful for controlled diagnosis but correlated, reducing effective sample independence. F-T01's “validates” versus “confirms effective” and F-T24's “countersignature” versus “ký xác nhận” are defensible paraphrases but should receive independent bilingual review before any contractual acceptance use. F-T22's “only via VPN after authorization” is a legitimate conditional answer, not an unconditional yes.

The author-written obligation strings are **not** authoritative policy interpretations for a deployable extractor. They are a reference for assessing the extraction/coverage split. Some are compressed (for example, “field-notes allowance amount”); independent annotation should separate requested relation, source-supported value, condition, and materiality. No new gold label is promoted to an approved release threshold or fixture.
