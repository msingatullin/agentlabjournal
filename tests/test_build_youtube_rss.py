import importlib.util
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("build_youtube_podcast_rss", ROOT / "scripts" / "build-youtube-podcast-rss.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_build_youtube_feed_is_separate_and_uses_audio_enclosures(tmp_path):
    source = tmp_path / "podcast-rss.xml"
    source.write_text(
        '''<?xml version="1.0"?><rss version="2.0" xmlns:itunes="http://www.itunes.apple.com/dtds/podcast-1.0.dtd" xmlns:atom="http://www.w3.org/2005/Atom"><channel>
        <title>Agent Lab Journal</title><link>https://agentlabjournal.online/podcasts.html</link>
        <atom:link href="https://agentlabjournal.online/podcast-rss.xml" rel="self" type="application/rss+xml"/>
        <itunes:image href="https://agentlabjournal.online/podcast-cover.png"/><item><title>Episode</title><guid>episode-1</guid><enclosure url="https://microsrv.online/podcasts/episode.mp3" type="audio/mp4" length="10"/></item>
        </channel></rss>''', encoding="utf-8"
    )
    output = tmp_path / "youtube-podcast-rss.xml"
    MODULE.build_youtube_feed(source, output)
    root = ET.parse(output).getroot()
    channel = root.find("channel")
    assert channel is not None
    assert channel.findtext("title") == "Agent Lab Journal Podcast — YouTube Music"
    image = channel.find("image")
    assert image is not None
    assert image.findtext("url") == "https://agentlabjournal.online/podcast-cover.png"
    owner = channel.find("{http://www.itunes.com/dtds/podcast-1.0.dtd}owner")
    assert owner is not None
    assert owner.findtext("{http://www.itunes.com/dtds/podcast-1.0.dtd}email") == "mmsingatullin@gmail.com"
    self_link = channel.find("{http://www.w3.org/2005/Atom}link")
    assert self_link is not None
    assert self_link.get("href") == "https://agentlabjournal.online/youtube-podcast-rss.xml"
    enclosure = channel.find("item/enclosure")
    assert enclosure is not None
    assert enclosure.get("type") == "audio/mpeg"
    assert enclosure.get("url", "").startswith("https://")
