# Agent Lab Dzen Newsroom Design

## Objective

Publish 15–20 original Russian-language Dzen articles per day across AI,
technology, money, and business. Every item must be useful rather than a dry
rewrite, contain a distinct editorial image, link to Agent Lab Journal, and
connect readers to related Dzen articles.

## Publication model

The website remains the source of truth. Each story is published as a public,
indexable HTML page and exported through `dzen-rss.xml`; Dzen imports the full
article. The scheduler distributes 18 daily slots between 08:00 and 23:00 MSK.
Publication is fail-closed: an item that misses evidence, originality, image,
SEO, link, or RSS gates stays in the queue.

## Editorial mix

- 35% AI products, models, agents, and automation.
- 25% technology platforms, cybersecurity, devices, and regulation.
- 25% money, markets, consumer finance, and the economics of technology.
- 15% companies, careers, work, and digital business.

Every story uses at least one current primary source. Material claims must be
traceable to a stored evidence record. The copy adds context: what happened,
why it matters, who is affected, what remains unknown, and one practical
consequence. Headlines must be distinct and non-clickbait. Near-duplicate
stories and repeated angles are blocked before publication.

## Article contract

Each page contains a unique H1, lead, 3–5 short sections, source attribution,
one lead image, optional inline images, and a final navigation block. The final
block contains one context-matching CTA to an Agent Lab Journal pillar page and
up to three related Dzen URLs from a maintained registry. Until a newly imported
item has a Dzen URL, only already verified Dzen URLs may be linked.

## Image contract

- Unique lead image for every story; shared series covers are forbidden.
- 16:9, target 1600×900, minimum 1200×675.
- JPEG or PNG, under 30 MB; RSS minimum width remains 700 px.
- No small text, fake UI, third-party watermark, or unlicensed logo collage.
- Provenance is recorded as generated editorial art, licensed press asset, or
  source asset with an explicit reuse basis.
- The same image is exposed as `og:image`, RSS `enclosure`, and the first
  `<figure><img>` inside `content:encoded` with useful alt/caption text.

## RSS contract

The feed preserves allowed links and formatting, emits H1 and full text in
CDATA, includes `figure/img` for the lead image, and emits `enclosure` with the
correct MIME type. Every item has stable canonical `guid`, RFC822 `pubDate`,
`format-article`, `index`, and `comment-all`; ordinary channel items omit
`author`. Feed size stays below 10 MiB and contains no more than 500 items.

## SEO and discovery

Every website story receives a query passport using current measured demand.
Primary intent and canonical URL must be unique; the page is added to sitemap
and internal navigation. Newly published URLs are submitted to Yandex.Webmaster
recrawl immediately and the response is recorded.

## State and safety

The newsroom queue stores source fingerprint, normalized headline/body hashes,
image provenance, validation results, scheduled slot, website URL, and Dzen URL.
Exact and near duplicates are rejected across website, Telegram imports, and
the Dzen registry. Publication retries use stable IDs and never create a second
item. Scheduled automation remains disabled until a real imported article is
visually checked in Dzen for image, links, formatting, and recommendation state.

## Acceptance

The launch gate requires: RSS contract tests pass; one live article renders on
the site with its unique image; its feed item contains clickable site and Dzen
links plus inline media; Dzen imports it without restriction; the imported
article is visually verified; and Yandex.Webmaster accepts the canonical URL.
After that check, enable the 18-slot daily schedule.
