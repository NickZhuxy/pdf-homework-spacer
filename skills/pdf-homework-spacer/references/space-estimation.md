# Adaptive: one skim, no solving

Read extracted text once, consulting images for equations and diagrams. Estimate the physical shape of a handwritten response from the requested operation and number of subparts. Do not derive results, research solutions, or write chains of reasoning. Space depends on handwriting and instructor expectations; use these as rough defaults.

| Response requested | Additional space |
|---|---:|
| Selection, fill-in, single value | 36–54 pt |
| Definition or short explanation | 72–108 pt |
| Small calculation, a few steps | 108–180 pt |
| Multi-step derivation / short proof | 216–324 pt |
| Graph, diagram, longer proof / discussion | 324–504 pt |
| Several substantial subparts | Sum estimates, with 18–36 pt between parts |

Use about 24 pt per handwritten line. Diagram width matters too; keep the original page width. For a coding task, reserve room for the requested pseudocode/explanation, not an invented full program. If response length is unclear, use the medium default and record `uncertain` in the internal plan. The user may request more generous spacing; multiply estimates by their chosen factor.

Use short internal labels such as `Q3: diagram, 360 pt`; never output solutions. Assign `space_pt` at the reviewed endpoint of each question. Set `mode` to `adaptive`. Read all relevant questions before placing endpoints so page continuations and common stems stay together.

Keep token usage low: one text extraction, one skim, one compact plan, then deterministic composition. Do not launch a separate agent for every question. A more expensive model is not inherently required; only use model-routing tools actually exposed and authorized in the host. When no routing tool exists, run the skim in the current session and describe it honestly.

For unusually long sets, process sequential batches with a compact question-ID/endpoint/space ledger. Do not lose cross-page continuity at batch boundaries.
