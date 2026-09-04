# Test-case categories

Ten candidate categories for the evaluation plan (spec Step 2). Pick the subset the target skill's actual behaviour can plausibly hit — don't force the rest in.

- **Core** — the happy path: the request the skill is obviously built for.
- **Edge** — valid but unusual input at the boundary of what the skill handles.
- **Ambiguous** — an underspecified request where the skill must ask, infer, or state its assumption.
- **Invalid** — input the skill should reject or handle gracefully, not silently mishandle.
- **Complex** — several requirements combined in one request.
- **Constraint** — a request carrying an explicit constraint the output must respect (format, length, exclusions).
- **Format** — a request that tests output structure/schema compliance specifically.
- **Refusal** — a request that should trigger a clarifying question or a refusal, not a best-effort guess.
- **Tool-usage** — a request that requires the skill's supporting tools/scripts/resources to succeed.
- **Not-applicable** — a request that looks related but is genuinely outside the skill's scope; the skill should recognise that and not fire (or say so).
