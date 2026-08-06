# Content Safety

**Layer:** Shared Document  
**Loaded by:** seo-article-writer, seo-editor, content-strategy  
**Purpose:** Hard limits on what agents may and may not assert in content. Safety constraints override all other instructions.

> **Maintenance rule:** Any constraint on what agents may and may not claim in content belongs here. Do NOT scatter safety rules across SKILL.md files.
>
> **Relationship to `eeat-framework.md`:** eeat-framework covers E-E-A-T principles — the WHY behind content quality. This document covers operational hard limits — the WHAT agents must and must not do. Do not duplicate eeat-framework content here; cross-reference it.

---

## YMYL Self-Identification

When the YMYL flag is provided in the runtime context, elevated standards apply automatically.

**When the YMYL flag is absent or unclear: default to treating the topic as YMYL.** Better to over-apply scrutiny than to publish inaccurate health or financial content.

Apply YMYL-level scrutiny to any topic that could directly affect a reader's health, financial stability, safety, or legal rights.

For the full YMYL category list and elevated E-E-A-T requirements, see `eeat-framework.md` (loaded automatically).

---

## Factual Claim Rules

Do not fabricate statistics, studies, or specific data points. Apply the Evidence Hierarchy from `eeat-framework.md` (loaded automatically) to all factual claims.

**When a specific claim is needed but no source is available:**
- Use the citation placeholder format from `eeat-framework.md` — do not invent a source
- Or describe the claim in general terms without fabricating precision: "research in this area suggests…" is acceptable; "A 2023 Harvard study found 73%…" without a real citation is not

**General knowledge threshold:**
- Well-established facts that any knowledgeable person in the field would know do not require a citation
- Specific numbers, named study findings, dates, and attributed claims always need a traceable source or a citation placeholder

---

## Medical, Legal, and Financial Content

There is a hard distinction between general information and specific advice.

**Permitted:**
- General information about how a medical condition, financial product, or legal concept works
- Describing common practices or typical outcomes at a population level
- Explaining options that a reader should explore with a qualified professional

**Not permitted:**
- Specific personal advice: specific diagnoses, specific treatment recommendations for the reader's situation, specific legal rulings applied to the reader's case, specific investment recommendations
- Claims that require credentials the client does not hold

**Required disclaimer:**

When content directly addresses a health, financial, legal, or safety decision a reader might act on, include a domain-appropriate disclaimer — e.g. "consult a qualified [doctor / financial advisor / solicitor]" or equivalent. The disclaimer must be specific to the domain; a generic "seek professional advice" without context is insufficient.

---

## Title and Headline Accuracy

Do not write a title or headline that overpromises what the content actually delivers. The title is a contract with the reader. Violating it increases bounce rate and signals low quality to Google's quality evaluators.

- "The Complete Guide to X" requires comprehensive coverage of X
- "How to X in Y Minutes" requires the content to genuinely show how to do X in that timeframe
- Superlatives ("the only", "the best ever", "the ultimate") require the claim to be verifiable or must be removed

---

## Potential Missing Rules (Not Added)

The following constraints do not exist in any production SKILL.md file. They are listed here as candidates for future addition.

**Third-party references:** Factual comparisons with competitors or other brands are acceptable. False or misleading claims about third parties are not. Defamatory content must not be written. No production source found to extract from.

**Privacy and PII:** Private individuals' personal information (names, contact details, addresses) should not appear in generated content. Business contact information provided in the knowledge base is acceptable. No production source found to extract from.
