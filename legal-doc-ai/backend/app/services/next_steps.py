from __future__ import annotations

from app.schemas.analysis import CoreExtraction, RetrievalHit


class NextStepsService:
    def suggest(self, text: str, extraction: CoreExtraction, retrieval: list[RetrievalHit]) -> list[str]:
        low = text.lower()
        steps: list[str] = []

        if "bail" in low and "modified" in low:
            steps.append("Ensure strict compliance with the modified bail terms and file proof of compliance before the concerned court.")

        if "cash surety" in low:
            steps.append("Verify cash surety amount and submission procedure before the Trial Court/Jail authority to avoid release delay.")

        if "section 528" in low:
            steps.append("Review judicial interpretation of Section 528 and prepare arguments on scope of bail-condition modification.")

        if "dismissed" in low:
            steps.append("Evaluate appellate remedy, limitation period, and grounds for challenge against dismissal.")

        if "allowed" in low:
            steps.append("Prepare implementation checklist of the allowed directions and confirm all operative conditions are satisfied.")

        if extraction.final_order and "released on bail" in extraction.final_order.value.lower():
            steps.append("Coordinate immediate filing of personal bond/surety documents to effectuate release order.")

        if retrieval:
            steps.append("Compare with retrieved precedents to confirm consistency in relief conditions and procedural compliance.")

        if not steps:
            steps.append("Conduct focused legal review of operative directions, statutory basis, and immediate compliance obligations.")

        deduped: list[str] = []
        seen: set[str] = set()
        for step in steps:
            key = step.lower()
            if key in seen:
                continue
            deduped.append(step)
            seen.add(key)
        return deduped
