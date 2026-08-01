#!/usr/bin/env python3
"""Build deterministic, source-based SVG covers for the homepage selection."""
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "covers"
OUT.mkdir(parents=True, exist_ok=True)

INK = "#17222d"
PAPER = "#f3f1eb"
MUTED = "#6c7478"
ACCENT = "#d9572b"
BLUE = "#277187"
PALE = "#dbe7e5"


def svg(slug: str, title: str, label: str, body: str) -> None:
    content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" role="img" aria-labelledby="title desc">
  <title id="title">{escape(title)}</title>
  <desc id="desc">{escape(body)}</desc>
  <rect width="1280" height="720" fill="{PAPER}"/>
  <path d="M64 82H1216M64 638H1216" stroke="{INK}" stroke-width="2"/>
  <text x="64" y="54" fill="{ACCENT}" font-family="DejaVu Sans, sans-serif" font-size="20" font-weight="700" letter-spacing="3">AGENT LAB / {escape(label)}</text>
  <text x="1216" y="54" text-anchor="end" fill="{MUTED}" font-family="DejaVu Sans Mono, monospace" font-size="17">FIELD NOTE · 2026</text>
  {body}
  <text x="64" y="686" fill="{INK}" font-family="DejaVu Sans, sans-serif" font-size="22" font-weight="700">{escape(title)}</text>
</svg>'''
    (OUT / f"{slug}.svg").write_text(content, encoding="utf-8")


svg(
    "llm-function-calling-provider-comparison",
    "Function calling: provider comparison",
    "TOOLS",
    f'''<g font-family="DejaVu Sans Mono, monospace">
  <rect x="64" y="136" width="330" height="414" fill="{INK}"/>
  <text x="96" y="188" fill="{PAPER}" font-size="21">ONE TEST SUITE</text>
  <text x="96" y="244" fill="{PALE}" font-size="18">01 route selection</text>
  <text x="96" y="286" fill="{PALE}" font-size="18">02 arguments</text>
  <text x="96" y="328" fill="{PALE}" font-size="18">03 schema errors</text>
  <text x="96" y="370" fill="{PALE}" font-size="18">04 tool failure</text>
  <path d="M96 426H350" stroke="{ACCENT}" stroke-width="5"/>
  <text x="96" y="478" fill="{PAPER}" font-size="17">EXPECTED != PLAUSIBLE</text>
  </g>
  <path d="M394 343H506" stroke="{INK}" stroke-width="3"/><path d="m490 331 20 12-20 12" fill="none" stroke="{INK}" stroke-width="3"/>
  <g font-family="DejaVu Sans, sans-serif" font-size="25" font-weight="700">
    <rect x="530" y="136" width="276" height="178" fill="{PALE}"/><text x="566" y="211" fill="{INK}">PROVIDER A</text><text x="566" y="255" fill="{BLUE}" font-size="18">native schema</text>
    <rect x="530" y="372" width="276" height="178" fill="{PALE}"/><text x="566" y="447" fill="{INK}">PROVIDER B</text><text x="566" y="491" fill="{BLUE}" font-size="18">native schema</text>
    <rect x="884" y="224" width="332" height="238" fill="none" stroke="{INK}" stroke-width="3"/><text x="920" y="304" fill="{INK}">TOOLS</text><text x="920" y="356" fill="{MUTED}" font-size="18">lookup · quote · cancel</text><text x="920" y="402" fill="{ACCENT}" font-size="18">compare actual calls</text>
  </g>
  <path d="M806 225H884M806 461H884" stroke="{INK}" stroke-width="3"/>''',
)

svg(
    "audit-claude-code-hidden-reminders",
    "Claude Code log audit",
    "OBSERVABILITY",
    f'''<rect x="64" y="126" width="1152" height="430" fill="{INK}"/>
  <g font-family="DejaVu Sans Mono, monospace" font-size="18">
    <text x="100" y="178" fill="{MUTED}">session.jsonl</text>
    <text x="100" y="224" fill="{PALE}">{{"type":"assistant","usage":{{...}}}}</text>
    <rect x="92" y="250" width="1096" height="58" fill="{BLUE}"/><text x="112" y="287" fill="{PAPER}">&lt;ip_reminder&gt; ... &lt;/ip_reminder&gt;</text>
    <text x="100" y="352" fill="{PALE}">{{"input_tokens":  —  , "cache_read":  —  }}</text>
    <text x="100" y="398" fill="{PALE}">{{"output_tokens": —  , "cache_create": —  }}</text>
    <path d="M100 446H742" stroke="{ACCENT}" stroke-width="6"/><path d="M100 482H968" stroke="{PALE}" stroke-width="6"/><path d="M100 518H548" stroke="{BLUE}" stroke-width="6"/>
    <text x="1010" y="454" fill="{PAPER}">COUNT</text><text x="1010" y="490" fill="{PAPER}">CACHE</text><text x="1010" y="526" fill="{PAPER}">OUTPUT</text>
  </g>''',
)

svg(
    "mcp-server-least-privilege",
    "MCP least privilege",
    "SECURITY",
    f'''<g font-family="DejaVu Sans, sans-serif">
  <text x="64" y="154" fill="{INK}" font-size="54" font-weight="700">One tool. One scope.</text>
  <g transform="translate(64 205)">
    <rect width="1152" height="330" fill="none" stroke="{INK}" stroke-width="3"/>
    <path d="M0 82H1152M0 164H1152M0 246H1152M420 0V330M690 0V330M930 0V330" stroke="{INK}" stroke-width="2"/>
    <g fill="{MUTED}" font-size="20"><text x="26" y="51">TOOL</text><text x="448" y="51">READ</text><text x="718" y="51">WRITE</text><text x="958" y="51">CLOSE</text></g>
    <g fill="{INK}" font-size="24" font-weight="700"><text x="26" y="135">ticket_search</text><text x="26" y="217">ticket_comment</text><text x="26" y="299">ticket_close</text></g>
    <g font-family="DejaVu Sans Mono, monospace" font-size="34" font-weight="700"><text x="488" y="135" fill="{BLUE}">YES</text><text x="758" y="135" fill="{MUTED}">NO</text><text x="998" y="135" fill="{MUTED}">NO</text><text x="488" y="217" fill="{BLUE}">YES</text><text x="758" y="217" fill="{ACCENT}">OWN</text><text x="998" y="217" fill="{MUTED}">NO</text><text x="488" y="299" fill="{BLUE}">YES</text><text x="758" y="299" fill="{MUTED}">NO</text><text x="998" y="299" fill="{ACCENT}">GATE</text></g>
  </g></g>''',
)

svg(
    "prompt-injection-tool-output",
    "Prompt injection through tool output",
    "SECURITY",
    f'''<g font-family="DejaVu Sans, sans-serif">
  <rect x="64" y="154" width="302" height="360" fill="{PALE}"/><text x="96" y="208" fill="{INK}" font-size="25" font-weight="700">UNTRUSTED</text><text x="96" y="250" fill="{MUTED}" font-size="18">page · email · API</text><path d="M96 306H326M96 350H286M96 394H316" stroke="{MUTED}" stroke-width="9"/><path d="M96 452H300" stroke="{ACCENT}" stroke-width="9"/>
  <path d="M366 334H500" stroke="{INK}" stroke-width="4"/><path d="m482 320 24 14-24 14" fill="none" stroke="{INK}" stroke-width="4"/>
  <rect x="520" y="120" width="322" height="428" fill="{INK}"/><text x="562" y="198" fill="{PAPER}" font-size="27" font-weight="700">POLICY GATE</text><text x="562" y="256" fill="{PALE}" font-size="18">data != instruction</text><text x="562" y="304" fill="{PALE}" font-size="18">capabilities = []</text><rect x="562" y="360" width="236" height="78" fill="{ACCENT}"/><text x="606" y="409" fill="{PAPER}" font-size="24" font-weight="700">DENY</text>
  <path d="M842 334H974" stroke="{INK}" stroke-width="4"/><path d="m956 320 24 14-24 14" fill="none" stroke="{INK}" stroke-width="4"/>
  <rect x="994" y="210" width="222" height="248" fill="none" stroke="{INK}" stroke-width="3"/><text x="1026" y="278" fill="{INK}" font-size="24" font-weight="700">ACTION</text><path d="M1026 326H1182" stroke="{MUTED}" stroke-width="8"/><path d="M1026 370H1136" stroke="{MUTED}" stroke-width="8"/><path d="M1026 414H1170" stroke="{MUTED}" stroke-width="8"/>
  </g>''',
)

svg(
    "rag-corpus-change-regression",
    "RAG corpus regression",
    "EVALUATION",
    f'''<g font-family="DejaVu Sans, sans-serif">
  <rect x="64" y="136" width="500" height="390" fill="{PALE}"/><text x="100" y="196" fill="{INK}" font-size="25" font-weight="700">BASELINE</text><text x="500" y="196" text-anchor="end" fill="{BLUE}" font-family="DejaVu Sans Mono, monospace" font-size="20">PASS</text>
  <rect x="716" y="136" width="500" height="390" fill="{INK}"/><text x="752" y="196" fill="{PAPER}" font-size="25" font-weight="700">CANDIDATE</text><text x="1152" y="196" text-anchor="end" fill="{ACCENT}" font-family="DejaVu Sans Mono, monospace" font-size="20">REGRESSION</text>
  <g font-family="DejaVu Sans Mono, monospace" font-size="18"><text x="100" y="260" fill="{MUTED}">retrieval  1.00</text><text x="100" y="314" fill="{MUTED}">citation   PASS</text><text x="100" y="368" fill="{MUTED}">answer     PASS</text><text x="752" y="260" fill="{PALE}">retrieval  0.00</text><text x="752" y="314" fill="{PALE}">citation   MISSING</text><text x="752" y="368" fill="{PALE}">answer     BLOCK</text></g>
  <path d="M100 430H518" stroke="{BLUE}" stroke-width="10"/><path d="M752 430H890" stroke="{ACCENT}" stroke-width="10"/>
  <path d="M586 330H694" stroke="{INK}" stroke-width="4"/><path d="m676 316 24 14-24 14" fill="none" stroke="{INK}" stroke-width="4"/>
  </g>''',
)

svg(
    "agent-trace-data-minimization",
    "Agent trace data minimization",
    "PRIVACY",
    f'''<g font-family="DejaVu Sans Mono, monospace">
  <rect x="64" y="130" width="1152" height="424" fill="{INK}"/>
  <text x="100" y="186" fill="{MUTED}" font-size="18">TRACE EVENT / BEFORE STORAGE</text>
  <text x="100" y="246" fill="{PAPER}" font-size="22">user_id</text><rect x="314" y="220" width="280" height="38" fill="{BLUE}"/><text x="628" y="246" fill="{PALE}" font-size="18">pseudonymized</text>
  <text x="100" y="312" fill="{PAPER}" font-size="22">prompt</text><rect x="314" y="286" width="640" height="38" fill="{ACCENT}"/><text x="988" y="312" fill="{PALE}" font-size="18">dropped</text>
  <text x="100" y="378" fill="{PAPER}" font-size="22">tool_args</text><rect x="314" y="352" width="520" height="38" fill="{ACCENT}"/><text x="868" y="378" fill="{PALE}" font-size="18">redacted</text>
  <text x="100" y="444" fill="{PAPER}" font-size="22">latency_ms</text><rect x="314" y="418" width="180" height="38" fill="{PALE}"/><text x="528" y="444" fill="{PALE}" font-size="18">kept</text>
  <text x="100" y="510" fill="{PAPER}" font-size="22">status</text><rect x="314" y="484" width="180" height="38" fill="{PALE}"/><text x="528" y="510" fill="{PALE}" font-size="18">kept</text>
  </g>''',
)

svg(
    "build-and-test-mcp-server",
    "Build and test an MCP server",
    "TOOLS",
    f'''<g font-family="DejaVu Sans, sans-serif">
  <rect x="64" y="184" width="260" height="286" fill="{INK}"/><text x="98" y="250" fill="{PAPER}" font-size="24" font-weight="700">LLM AGENT</text><text x="98" y="298" fill="{PALE}" font-size="18">MCP client</text><text x="98" y="346" fill="{PALE}" font-size="18">tool call</text>
  <path d="M324 327H466" stroke="{INK}" stroke-width="4"/><path d="m448 313 24 14-24 14" fill="none" stroke="{INK}" stroke-width="4"/>
  <rect x="486" y="126" width="322" height="402" fill="{PALE}"/><text x="524" y="194" fill="{INK}" font-size="25" font-weight="700">MCP SERVER</text><text x="524" y="246" fill="{BLUE}" font-family="DejaVu Sans Mono, monospace" font-size="18">tools/list</text><text x="524" y="294" fill="{BLUE}" font-family="DejaVu Sans Mono, monospace" font-size="18">tools/call</text><text x="524" y="342" fill="{BLUE}" font-family="DejaVu Sans Mono, monospace" font-size="18">schema</text><rect x="524" y="400" width="246" height="72" fill="{ACCENT}"/><text x="568" y="445" fill="{PAPER}" font-size="21" font-weight="700">TEST PASS</text>
  <path d="M808 327H950" stroke="{INK}" stroke-width="4"/><path d="m932 313 24 14-24 14" fill="none" stroke="{INK}" stroke-width="4"/>
  <rect x="970" y="184" width="246" height="286" fill="none" stroke="{INK}" stroke-width="3"/><text x="1004" y="250" fill="{INK}" font-size="24" font-weight="700">HTTP API</text><text x="1004" y="298" fill="{MUTED}" font-family="DejaVu Sans Mono, monospace" font-size="18">request</text><text x="1004" y="346" fill="{MUTED}" font-family="DejaVu Sans Mono, monospace" font-size="18">response</text><text x="1004" y="394" fill="{MUTED}" font-family="DejaVu Sans Mono, monospace" font-size="18">audit log</text>
  </g>''',
)

print(f"EDITORIAL_COVERS: built 7 SVG covers in {OUT}")
