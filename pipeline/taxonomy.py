#!/usr/bin/env python3
"""Normalize legacy benchmark labels into two orthogonal product axes."""

from __future__ import annotations


CAPABILITY_GROUPS = {
    "Knowledge & Reasoning",
    "Mathematics & Formal Sciences",
    "Coding & Software Engineering",
    "Agents",
    "Tool Calling",
    "Computer Use",
    "Search & Retrieval",
    "Long Context & Memory",
    "Instruction Following & Structured Output",
    "Language & Communication",
    "Multimodal Perception",
    "Safety & Trustworthiness",
    "Systems & Efficiency",
    "Robotics & Embodied Intelligence",
}

AREA_TO_CAPABILITY = {
    "Language & Knowledge": "Knowledge & Reasoning",
    "Knowledge & Reasoning": "Knowledge & Reasoning",
    "Medical Reasoning": "Knowledge & Reasoning",
    "Factuality & Grounding": "Knowledge & Reasoning",
    "Mathematical Reasoning": "Mathematics & Formal Sciences",
    "Code & Software": "Coding & Software Engineering",
    "Agents & Tool Use": "Agents",
    "Computer Use": "Computer Use",
    "Long Context": "Long Context & Memory",
    "Instruction Following": "Instruction Following & Structured Output",
    "Language & Communication": "Language & Communication",
    "Vision & 3D": "Multimodal Perception",
    "Multimodal": "Multimodal Perception",
    "Multimodal Understanding": "Multimodal Perception",
    "Chart Understanding": "Multimodal Perception",
    "Video Understanding": "Multimodal Perception",
    "Speech & Audio": "Multimodal Perception",
    "Safety & Trustworthiness": "Safety & Trustworthiness",
    "Systems & Efficiency": "Systems & Efficiency",
    "Robotics & Embodied AI": "Robotics & Embodied Intelligence",
    "Science & Engineering": "Knowledge & Reasoning",
}

DOMAIN_MAP = {
    "Biology & Drug Discovery": "Health & Life Sciences",
    "Health & Biomedicine": "Health & Life Sciences",
    "Finance": "Finance & Economics",
    "Cybersecurity": "Cybersecurity",
    "Science": "Science & Research",
    "Scientific Research & AI for Science": "Science & Research",
    "Scientific Facilities": "Science & Research",
    "Materials & Chemistry": "Science & Research",
    "Quantum Computing & Control": "Science & Research",
    "Autonomous Driving": "Transport & Logistics",
    "Logistics & Operations": "Transport & Logistics",
    "Chip Design & EDA": "Industrial & Engineering",
    "Manufacturing & Process Control": "Industrial & Engineering",
    "Mobile & Personal Computing": "Consumer & Productivity",
    "Robotics & Embodied AI": "Robotics & Autonomous Systems",
}

TECHNICAL_DOMAIN_LABELS = {
    "General AI",
    "Software & AI Compute",
    "Mathematics",
    "Mathematics & Formal Science",
    "Multimodal",
}

TECHNICAL_DOMAIN_TO_CAPABILITY = {
    "Software & AI Compute": "Coding & Software Engineering",
    "Mathematics": "Mathematics & Formal Sciences",
    "Mathematics & Formal Science": "Mathematics & Formal Sciences",
    "Multimodal": "Multimodal Perception",
}


def unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def normalize_taxonomy(record: dict) -> dict:
    """Return normalized capability and application fields without text inference."""
    groups = [AREA_TO_CAPABILITY.get(record.get("area", ""), "Knowledge & Reasoning")]
    capabilities = set(record.get("capabilities") or [])
    topics = set(record.get("topics") or [])
    if "Tool use" in capabilities or "Tool Calling" in topics:
        groups.append("Tool Calling")
    if "Information retrieval" in capabilities or "Search" in topics:
        groups.append("Search & Retrieval")
    if "Code generation" in capabilities:
        groups.append("Coding & Software Engineering")
    if "Long Context" in topics:
        groups.append("Long Context & Memory")
    technical_groups = [
        TECHNICAL_DOMAIN_TO_CAPABILITY[domain]
        for domain in record.get("applicationDomains") or [record.get("primaryDomain")]
        if domain in TECHNICAL_DOMAIN_TO_CAPABILITY
    ]
    if technical_groups and groups == ["Knowledge & Reasoning"]:
        groups = []
    groups.extend(technical_groups)
    groups = unique(groups)[:3]

    source_domains = record.get("applicationDomains") or [record.get("primaryDomain")]
    domains = unique([
        DOMAIN_MAP.get(domain, domain)
        for domain in source_domains
        if domain and domain not in TECHNICAL_DOMAIN_LABELS
    ])
    if len(domains) > 1:
        scope = "cross-domain"
    elif domains:
        scope = "specific"
    elif any(domain in TECHNICAL_DOMAIN_LABELS for domain in source_domains if domain):
        scope = "general"
    else:
        scope = "unspecified"
    return {
        "capabilityGroups": groups,
        "applicationDomains": domains,
        "domainScope": scope,
        # Compatibility for the current Radar and Trends while the UI migrates.
        "primaryDomain": domains[0] if domains else "General AI",
    }
