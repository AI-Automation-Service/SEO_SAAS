# Meta Tag Optimizer — Domain Expertise

---

## Title Tag Rules

- Maximum 60 characters — Google truncates beyond this (pixel limit ~580–600px).
- `main_keyword` must appear in the first half of the title.
- After the pipe separator, write a SHORT compelling differentiator — an outcome, unique value, or what makes this business different.
- NEVER repeat the keyword or brand name after the pipe if it is the same as or similar to the keyword.
- Format: "[Main Keyword] | [Compelling Differentiator]"
- Good examples: "AI Consultant Services | Custom AI Built for Your Business" / "SEO Audit Tool | Catch Issues Before Google Does"
- Bad example: "AI Consultant Services | AI Consultant Service" (keyword repeated — forbidden)
- Do NOT use template variables like %%title%% or %%sitename%%.
- For homepages: title can be "[Brand Name] — [Value Proposition]" format instead of pipe format.
- Front-load the primary keyword — it signals relevance and improves CTR.
- Numbers, questions, and power words ("Fast", "Free", "Proven") can boost CTR ~36%.
- If `current_meta_title` is already keyword-optimized, non-redundant, and under 60 characters, return it unchanged.

---

## Meta Description Rules

- Target 140–155 characters for Latin scripts — Google truncates beyond ~160 characters.
- First sentence must directly answer what someone searching `main_keyword` wants.
- Naturally include the target keyword in the description.
- End with a subtle call-to-action or value differentiator.
- Do NOT use template variables.
- Match search intent: informational queries need an answer; commercial queries need a value prop; transactional queries need an action.
- For high CTR: include a specific benefit or number ("Cut your reporting time by 70%"), avoid generic phrases ("We offer the best...").
- If `current_meta_description` is already compelling, intent-matching, and under 155 characters, return it unchanged.

---

## Intent-by-Page-Type

| Page type | Title approach | Description approach |
|---|---|---|
| Homepage | Brand + core value proposition | What you do + who you serve + CTA |
| Service page | Service keyword + outcome | Problem solved + differentiator + CTA |
| Blog/article | Question or "how to" + keyword | Answer teaser + depth signal + CTA |
| Product page | Product + key benefit | Specific feature + proof + action |
| Category/archive | Topic scope + breadth signal | Range description + discovery CTA |


