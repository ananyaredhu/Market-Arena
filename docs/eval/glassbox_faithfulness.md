# Glass-Box faithfulness report

*Generated 2026-10-15 05:15 UTC · provider chain `groq` · model `openai/gpt-oss-120b` · 50 customers sampled (seed 7) from the 80-customer SaaS fixture, two scenarios (S$7 and S$3).*

**What is measured.** The Glass-Box explanation for each customer is built in four steps: code computes the numbers, the LLM only rephrases them, a verifier gates the sentence in real time, and a template replaces it if it fails. An *independent audit* (separate code, checked against the engine's unrounded numbers) then tests every sentence for: only real numbers, only real reasons, the main reason named, reasons that counted against the choice framed as such, only options that are part of the decision, no false "what would win you" claim for a customer who already chose you, and length.

| Measure | Passed | Rate | 95% interval | |
|---|---|---|---|---|
| **Delivered sentences faithful** (everything a user would see, LLM or template) | 50 / 50 | 100% | 93% to 100% |  **meets target** |
| ...of which written by the LLM | 50 / 50 | 100% | 93% to 100% |  **meets target** |
| LLM first answers faithful (before the verifier could reject or retry them) | 50 / 50 | 100% | 93% to 100% | |
| Template sentences faithful (no LLM, all customers) | 160 / 160 | 100% | 98% to 100% |  **meets target** |

Customers where the LLM answered: 50 of 50 (0 skipped because the provider was unavailable or rate-limited; they are not counted as faithful or unfaithful).

## How the delivered sentences were produced

| Outcome | Customers |
|---|---|
| LLM sentence accepted on the first try | 49 |
| LLM sentence accepted after the verifier sent it back | 1 |
| Verifier rejected the LLM; template shown instead | 0 |

**Gate escapes** (the verifier accepted a sentence the audit then failed): 0

## What the LLM got wrong on its first try

No first answer failed any check in this sample.

## Sample of sentences delivered to users

- `a053` (llm): The customer chose ChainApp because its features were the strongest factor, even though price was a concern.
- `a072` (llm): They chose the Free planner because of brand preference, even though the appeal of doing nothing was a factor.
- `a033` (llm): The customer chose Do nothing because the switching cost (0.47) was the biggest factor, even though features (0.6) counted against the choice.
- `a058` (llm): They chose StudyFlow because its features were most compelling, even though price was a concern.
- `a054` (llm): They chose ChainApp because its features (size 1.51) were the biggest draw, even though price (size 0.77) and the appeal of doing nothing (size 0.46) counted against it.
- `a078` (llm): The customer chose the Free planner because of strong brand preference, even though the appeal of doing nothing counted against it.
- `a059` (llm): The customer chose Do nothing because the appeal of doing nothing (size 0.41) outweighed other options, even though features (size 1.17) counted against the choice.
- `a005` (llm): The customer chose StudyFlow despite concerns about price, brand preference and switching cost.

## What running this evaluation changed

Measuring found real problems, each fixed and covered by a test:

- The template (the fallback) broke its own three-sentence rule for a customer who was both pinned and an unlikely draw. Fixed by merging two notes into one sentence.
- A real number attached to the *wrong reason* (for example the switching-cost size next to "features") passed a plain "is this number in the facts?" check. Added a number-to-reason binding check to the gate and the audit.
- Two reasons within 0.001 of each other were treated as a "biggest" and a "second", so a correct sentence naming either was rejected. Reasons within 10% of the biggest now tie for main reason.
- The evaluation itself double-counted the same customer across two scenarios (identical facts, served from cache) and mislabelled cache hits as provider outages. Fixed.

## Limits

- The audit checks numbers, named reasons, direction and options. It cannot judge every nuance of wording (for example whether "most compelling" is an apt phrase).
- 50 customers is a small sample; read the interval, not just the percentage.
- Customers come from one fixture population in one product category.
- The audit and the verifier share a vocabulary of reason words, so both can miss an unusual synonym.
