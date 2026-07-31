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

    return {
        "url": url,
        "strategy": strategy,
        "performance_score": round(perf_score * 100),
        "metrics": metrics,
    }
