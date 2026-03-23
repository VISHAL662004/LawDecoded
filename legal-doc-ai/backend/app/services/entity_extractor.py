from __future__ import annotations

import re
from collections import defaultdict

from app.schemas.analysis import CoreExtraction, ExtractedEntity, SourceSpan

DATE_PATTERN = re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b")
SECTION_PATTERN = re.compile(r"\b(?:Section|Sec\.|Article)\s+([0-9A-Za-z()/-]+)", re.IGNORECASE)
PUNISHMENT_PATTERN = re.compile(
    r"\b(?:imprisonment|fine of|sentence(?:d)? to|rigorous imprisonment)\b[^.]{0,200}",
    re.IGNORECASE,
)
PARTY_PATTERN = re.compile(r"([A-Z][A-Za-z\s.&]+)\s+(?:v\.?|versus)\s+([A-Z][A-Za-z\s.&]+)", re.IGNORECASE)
ORDER_PATTERN = re.compile(r"(?:ordered that|appeal is|petition is|disposed of|dismissed|allowed|modified|directed|released|granted)[^.]{0,260}", re.IGNORECASE)
COURT_PATTERN = re.compile(r"\b(?:Supreme Court of India|High Court of [A-Za-z\s]+|District Court [A-Za-z\s]+)\b", re.IGNORECASE)

JUDGE_PATTERNS = [
    re.compile(r"HON'?BLE[^\n]{0,40}JUSTICE\s+([A-Z][A-Za-z\s.]+)", re.IGNORECASE),
    re.compile(r"JUSTICE\s+([A-Z][A-Za-z\s.]+)", re.IGNORECASE),
    re.compile(r"\b([A-Z][A-Za-z\s.]+),\s*J\.?\b"),
]


class EntityExtractionService:
    def extract(self, text: str) -> CoreExtraction:
        entities = defaultdict(list)

        case_name = None
        party_match = PARTY_PATTERN.search(text)
        if party_match:
            petitioner = party_match.group(1).strip()
            respondent = party_match.group(2).strip()
            full = f"{petitioner} v. {respondent}"
            case_name = self._entity("CASE_NAME", full, text)
            entities["parties"].append(self._entity("PETITIONER", petitioner, text))
            entities["parties"].append(self._entity("RESPONDENT", respondent, text))

        header = self._header_region(text)
        header_judges = self._extract_judges(header, text, confidence=0.95)
        if header_judges:
            entities["judges"].extend(header_judges)
        else:
            entities["judges"].extend(self._extract_judges(text, text, confidence=0.78))

        coram_judges = self._extract_coram_judges(text)
        entities["judges"].extend(coram_judges)

        for m in DATE_PATTERN.finditer(text):
            entities["important_dates"].append(self._entity("DATE", m.group(0), text))

        for m in SECTION_PATTERN.finditer(text):
            entities["legal_sections_cited"].append(
                self._entity("SECTION_OF_LAW", f"Section {m.group(1)}", text)
            )

        for m in PUNISHMENT_PATTERN.finditer(text):
            entities["punishment_sentence"].append(
                self._entity("PUNISHMENT", m.group(0).strip(), text)
            )

        for m in COURT_PATTERN.finditer(text):
            entities["court_names"].append(self._entity("COURT_NAME", m.group(0).strip(), text))

        final_order = self._extract_final_order(text)

        return CoreExtraction(
            case_name=case_name,
            parties=self._dedupe(entities["parties"]),
            judges=self._dedupe(entities["judges"]),
            court_names=self._dedupe(entities["court_names"]),
            important_dates=self._dedupe(entities["important_dates"]),
            legal_sections_cited=self._dedupe(entities["legal_sections_cited"]),
            punishment_sentence=self._dedupe(entities["punishment_sentence"]),
            final_order=final_order,
        )

    def _header_region(self, text: str) -> str:
        lines = text.splitlines()
        n = max(1, int(len(lines) * 0.25))
        return "\n".join(lines[:n])

    def _extract_judges(self, region: str, full_text: str, confidence: float) -> list[ExtractedEntity]:
        found: list[ExtractedEntity] = []
        for pat in JUDGE_PATTERNS:
            for m in pat.finditer(region):
                raw = m.group(1) if m.groups() else m.group(0)
                name = self._normalize_judge_name(raw)
                if len(name.split()) < 2:
                    continue
                found.append(self._entity("JUDGE", name, full_text, confidence=confidence))
        return found

    def _extract_coram_judges(self, text: str) -> list[ExtractedEntity]:
        out: list[ExtractedEntity] = []
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if "coram" in line.lower():
                window = " ".join(lines[i : i + 6])
                out.extend(self._extract_judges(window, text, confidence=0.92))
        return out

    def _normalize_judge_name(self, name: str) -> str:
        clean = re.sub(r"\b(HON'?BLE|MR\.?|MS\.?|MRS\.?|JUSTICE|J\.?|CORAM)\b", "", name, flags=re.IGNORECASE)
        clean = re.sub(r"\bORDER\b.*$", "", clean, flags=re.IGNORECASE)
        clean = re.sub(r"\s+", " ", clean).strip(" .,:;-")
        return clean.title()

    def _extract_final_order(self, text: str) -> ExtractedEntity | None:
        candidates = [m.group(0).strip() for m in ORDER_PATTERN.finditer(text)]
        if not candidates:
            return None

        weighted = []
        for cand in candidates:
            low = cand.lower()
            score = 0
            for kw in ["allowed", "dismissed", "released", "directed", "modified", "granted", "ordered"]:
                if kw in low:
                    score += 1
            if "exemption allowed" in low:
                score -= 2
            weighted.append((score, cand))
        weighted.sort(key=lambda x: x[0])
        picked = weighted[-1][1]
        return self._entity("FINAL_ORDER", picked, text, confidence=0.86)

    def _entity(self, label: str, value: str, text: str, confidence: float = 0.75) -> ExtractedEntity:
        start = text.lower().find(value.lower())
        end = start + len(value) if start >= 0 else 0
        return ExtractedEntity(
            label=label,
            value=value,
            confidence=confidence,
            source=SourceSpan(text=value, start_char=max(start, 0), end_char=end, page=None),
        )

    def _dedupe(self, entities: list[ExtractedEntity]) -> list[ExtractedEntity]:
        seen: set[str] = set()
        out: list[ExtractedEntity] = []
        for e in entities:
            key = f"{e.label}:{e.value.lower()}"
            if key not in seen:
                out.append(e)
                seen.add(key)
        return out
