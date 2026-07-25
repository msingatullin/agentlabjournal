"""Single UTM contract for every Agent Lab Journal publication."""
from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl
import re


def slug(value: str, fallback: str = "all") -> str:
    value = re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")
    return value or fallback


def tracked_url(canonical: str, source: str, medium: str, article: str,
                language: str = "en", country: str = "global",
                region: str = "all", content: str = "article") -> str:
    parts = urlsplit(canonical)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query.update({
        "utm_source": slug(source),
        "utm_medium": slug(medium),
        "utm_campaign": f"agentlabjournal-{slug(language)}-{slug(country)}-{slug(region)}",
        "utm_content": slug(content),
        "utm_term": slug(article, "article"),
    })
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
