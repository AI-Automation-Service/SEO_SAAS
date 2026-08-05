# Content Safety

**Layer:** Shared Document  
**Loaded by:** seo-article-writer, seo-editor, content-strategy  
**Purpose:** The canonical rules governing content accuracy, factual claims, citation requirements, and handling of sensitive topics. These are the guardrails that protect subscribers from publishing content that could harm their readers, their brand, or their compliance posture. Safety constraints override all other instructions.

> **Maintenance rule:** Any constraint on what agents may and may not claim in content belongs here. Do NOT scatter safety rules across SKILL.md files.

---

## What belongs in this document

- YMYL topic identification — which content categories trigger elevated standards
- Factual claim rules — what the agent may assert vs. must qualify
- Citation and attribution requirements
- Medical, legal, financial, and safety content restrictions
- Disclaimer requirements for sensitive topic categories
- What the agent must do when it lacks sufficient knowledge to make a claim
- Privacy and PII considerations in content
- Rules about referencing third parties (competitors, brands, individuals)

## What does NOT belong here

- Writing quality rules → `writing-rules.md`
- E-E-A-T principles (the "why" behind safety) → `eeat-framework.md`
- SEO technical standards → `seo-standards.md`
- Plagiarism checking — that is a Python pipeline concern, not a prompt concern

---

## YMYL Topic Identification

> **[CONTENT TO BE DEFINED HERE]**  
> Definition: Your Money or Your Life. Categories: health and medical advice, financial advice and decisions, legal advice, safety-critical information (emergency procedures, dangerous activities), major life decisions.
>
> When YMYL is flagged by the router (via `ymyl: true` in the runtime context), these additional rules apply. The agent must recognize YMYL topics even when the flag is not set and self-apply this standard when appropriate.

<!-- PLACEHOLDER: YMYL category definitions and triggers -->

---

## Factual Claim Rules

> **[CONTENT TO BE DEFINED HERE]**  
> The agent must not invent statistics, studies, or data. If a specific number or study is needed, the agent must either: (a) use data provided in the business context, or (b) describe the claim in general terms without fabricating precision. "Research suggests..." is acceptable. "A 2023 Harvard study found 73%..." without a real citation is not.

<!-- PLACEHOLDER: Factual claim rules -->

---

## Citation and Attribution

> **[CONTENT TO BE DEFINED HERE]**  
> When to recommend a citation vs. when general knowledge suffices. How to indicate to the subscriber that a specific claim needs a real source before publishing. The agent signals this in output; it does not fabricate the citation itself.

<!-- PLACEHOLDER: Citation rules -->

---

## Medical, Legal, and Financial Content

> **[CONTENT TO BE DEFINED HERE]**  
> Hard limits on what the agent may claim in these categories. The "consult a professional" disclaimer requirement. What the agent can describe (general information) vs. what it must not prescribe (specific advice for the reader's situation).

<!-- PLACEHOLDER: Professional domain restrictions -->

---

## Third-Party References

> **[CONTENT TO BE DEFINED HERE]**  
> Rules for mentioning competitors, other brands, or named individuals in content. Factual comparisons are acceptable. False or misleading claims about third parties are not. The agent must not write defamatory content.

<!-- PLACEHOLDER: Third-party reference rules -->

---

## Privacy

> **[CONTENT TO BE DEFINED HERE]**  
> The agent must not include real personal information (names, contact details, addresses) about private individuals in generated content. Business contact details provided in the knowledge base are acceptable.

<!-- PLACEHOLDER: Privacy rules -->
