#!/usr/bin/env python3
"""Build the dedicated RSS feed imported by YouTube/YouTube Music.

The existing ``podcast-rss.xml`` remains the Yandex-facing feed. This builder
creates a separate, standard podcast RSS document with stable GUIDs and public
audio enclosures, so the two platform integrations can evolve independently.
"""
from __future__ import annotations

import argparse
import copy
import xml.etree.ElementTree as ET
from pathlib import Path

ATOM_NS = "http://www.w3.org/2005/Atom"
ITUNES_NS = "http://www.itunes.com/dtds/podcast-1.0.dtd"
PUBLIC_URL = "https://agentlabjournal.online/youtube-podcast-rss.xml"
IMAGE_URL = "https://agentlabjournal.online/podcast-cover.png"
OWNER_EMAIL = "mmsingatullin@gmail.com"

ET.register_namespace("atom", ATOM_NS)
ET.register_namespace("itunes", ITUNES_NS)


def build_youtube_feed(source: Path, output: Path) -> None:
    tree = ET.parse(source)
    root = tree.getroot()
    channel = root.find("channel")
    if channel is None:
        raise ValueError("RSS channel is missing")

    title = channel.find("title")
    if title is not None:
        title.text = "Agent Lab Journal Podcast — YouTube Music"
    atom_self = channel.find(f"{{{ATOM_NS}}}link")
    if atom_self is None:
        atom_self = ET.Element(f"{{{ATOM_NS}}}link")
        channel.insert(0, atom_self)
    atom_self.set("href", PUBLIC_URL)
    atom_self.set("rel", "self")
    atom_self.set("type", "application/rss+xml")

    # YouTube's RSS importer requires both a standard RSS image and an owner
    # email (used to send the ownership verification code).
    image = channel.find("image")
    if image is None:
        image = ET.Element("image")
        channel.insert(1, image)
    for tag, value in (("url", IMAGE_URL), ("title", "Agent Lab Journal Podcast"), ("link", "https://agentlabjournal.online/podcasts.html")):
        child = image.find(tag)
        if child is None:
            child = ET.SubElement(image, tag)
        child.text = value
    owner = channel.find(f"{{{ITUNES_NS}}}owner")
    if owner is None:
        owner = ET.Element(f"{{{ITUNES_NS}}}owner")
        channel.append(owner)
    owner_name = owner.find(f"{{{ITUNES_NS}}}name")
    if owner_name is None:
        owner_name = ET.SubElement(owner, f"{{{ITUNES_NS}}}name")
    owner_name.text = "Agent Lab Journal"
    owner_email = owner.find(f"{{{ITUNES_NS}}}email")
    if owner_email is None:
        owner_email = ET.SubElement(owner, f"{{{ITUNES_NS}}}email")
    owner_email.text = OWNER_EMAIL

    # YouTube imports standard podcast enclosures; normalize legacy mp4 labels
    # without mutating the Yandex source feed.
    for item in channel.findall("item"):
        enclosure = item.find("enclosure")
        if enclosure is not None:
            enclosure.set("type", "audio/mpeg")
            if not enclosure.get("url", "").startswith(("https://", "http://")):
                raise ValueError("podcast enclosure URL must be public HTTP(S)")
        if item.find("guid") is None:
            raise ValueError("each episode must have a stable guid")

    output.parent.mkdir(parents=True, exist_ok=True)
    ET.indent(root, space="  ")
    ET.ElementTree(root).write(output, encoding="utf-8", xml_declaration=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parent.parent / "podcast-rss.xml")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent.parent / "youtube-podcast-rss.xml")
    args = parser.parse_args()
    build_youtube_feed(args.source, args.output)
    print(f"YOUTUBE_RSS: built {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
