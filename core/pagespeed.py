import httpx

PSI_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

_AUDITS = {
    "fcp": "first-contentful-paint",
    "lcp": "largest-contentful-paint",
    "tbt": "total-blocking-time",
    "cls": "cumulative-layout-shift",
    "si":  "speed-index",
    "tti": "interactive",
}


def fetch_pagespeed(url: str, strategy: str = "mobile", api_key: str | None = None) -> dict:
    params: dict = {"url": url, "strategy": strategy}
    if api_key:
        params["key"] = api_key

    with httpx.Client(timeout=30) as client:
        resp = client.get(PSI_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

    lhr = data.get("lighthouseResult", {})
    audits = lhr.get("audits", {})
    perf_score = (lhr.get("categories", {}).get("performance", {}).get("score") or 0)

    metrics = {}
    for key, audit_id in _AUDITS.items():
        audit = audits.get(audit_id, {})
        metrics[key] = {
            "display": audit.get("displayValue", "—"),
            "value": audit.get("numericValue"),
            "score": audit.get("score"),
        }

    # Opportunities — audits with type=opportunity and meaningful savings
    opportunities = []
    for audit_id, audit in audits.items():
        score = audit.get("score")
        display = audit.get("displayValue", "")
        details = audit.get("details") or {}
        if (
            score is not None
            and score < 1
            and display
            and details.get("type") == "opportunity"
        ):
            savings_ms = details.get("overallSavingsMs") or 0
            if savings_ms >= 50:
                opportunities.append({
                    "id": audit_id,
                    "title": audit.get("title", ""),
                    "display": display,
                    "score": score,
                    "savings_ms": round(savings_ms),
                })

    opportunities.sort(key=lambda x: x["savings_ms"], reverse=True)

    # Diagnostics — non-opportunity audits that failed
    diagnostics = []
    for audit_id, audit in audits.items():
        score = audit.get("score")
        details = audit.get("details") or {}
        if (
            score is not None
            and score < 1
            and details.get("type") not in ("opportunity",)
            and audit.get("scoreDisplayMode") not in ("informative", "notApplicable", "manual")
            and audit.get("displayValue")
        ):
            diagnostics.append({
                "id": audit_id,
                "title": audit.get("title", ""),
                "display": audit.get("displayValue", ""),
                "score": score,
            })

    diagnostics.sort(key=lambda x: x["score"])

    return {
        "url": url,
        "strategy": strategy,
        "performance_score": round(perf_score * 100),
        "metrics": metrics,
        "opportunities": opportunities[:10],
        "diagnostics": diagnostics[:8],
    }
