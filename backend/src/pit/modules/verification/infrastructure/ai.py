"""Proof verifiers: a vision LLM in production, a lenient stand-in for local development."""

import base64
import json
import logging
from dataclasses import replace
from typing import Any

from pit.modules.verification.application.ports import ProofVerifier, VerificationRequest
from pit.modules.verification.domain.verdict import AiDecision, AiVerdict
from pit.modules.verification.infrastructure.storage import FileStorage
from pit.shared.infrastructure.llm import LlmPool

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Siz shaxsiy rivojlanish platformasida bajarilgan ish isbotini tekshiruvchisiz.
Foydalanuvchi bugungi vazifani bajarganini isbotlovchi rasm va/yoki matn yubordi.
Qoidalar:
- Faqat berilgan mezon va bugungi vazifa bo'yicha baholang.
- Shubhangiz bo'lsa, confidence'ni past qo'ying — noaniq holatlarni inson tekshiradi.
- Internetdan olinganga, skrinshotga yoki boshqa odamning rasmiga o'xshasa — reject.
- Kutilgan kod berilgan bo'lsa, rasmda qog'ozga yozilgan kodni toping va detected_code ga
  aynan yozing; topilmasa null qo'ying.
- reason foydalanuvchiga ko'rsatiladi: o'zbek tilida, bitta qisqa gap, hurmat bilan."""

VERDICT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "decision": {"type": "string", "enum": ["approve", "reject"]},
        "confidence": {"type": "number"},
        "reason": {"type": "string"},
        "detected_code": {"type": ["string", "null"]},
    },
    "required": ["decision", "confidence", "reason", "detected_code"],
    "additionalProperties": False,
}


def _parse_verdict(raw: str) -> AiVerdict:
    data = json.loads(raw)
    return AiVerdict(
        decision=AiDecision(data["decision"]),
        confidence=min(max(float(data["confidence"]), 0.0), 1.0),
        reason=str(data["reason"])[:300],
        model="",  # filled in with the provider that answered
        detected_code=data.get("detected_code"),
    )


class LlmProofVerifier:
    """A vision model from the AI pool judges the proof; whichever provider answers first."""

    def __init__(self, pool: LlmPool, storage: FileStorage) -> None:
        self._pool = pool
        self._storage = storage

    async def verify(self, request: VerificationRequest) -> AiVerdict:
        text = (
            f"Kategoriya: {request.category}\n"
            f"Mezon: {request.criteria}\n"
            f"Kutilgan kod: {request.expected_code or 'talab qilinmaydi'}\n"
            f"Foydalanuvchi matni: {request.text_note or '—'}"
        )
        content: list[dict[str, Any]] = [{"type": "text", "text": text}]
        if request.file_key:
            image = base64.b64encode(await self._storage.get(request.file_key)).decode()
            content.append(
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image}"}}
            )
        verdict, label = await self._pool.complete(
            temperature=0,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "proof_verdict", "strict": True, "schema": VERDICT_SCHEMA},
            },
            parse=_parse_verdict,
        )
        return replace(verdict, model=label)


class ResilientVerifier:
    """If the AI is down or answers garbage, never punish the user for it: the proof is
    treated as a doubtful approval — free mode passes, stake mode goes to a moderator."""

    def __init__(self, inner: ProofVerifier) -> None:
        self._inner = inner

    async def verify(self, request: VerificationRequest) -> AiVerdict:
        try:
            return await self._inner.verify(request)
        except Exception:
            logger.exception("AI verification failed for proof %s", request.proof_id)
            return AiVerdict(
                decision=AiDecision.APPROVE,
                confidence=0.5,
                reason="Avtomatik tekshiruv vaqtincha ishlamadi",
                model="fallback",
                detected_code=request.expected_code,
            )


class DevProofVerifier:
    """Local development without an AI key: approves everything and says so."""

    async def verify(self, request: VerificationRequest) -> AiVerdict:
        return AiVerdict(
            decision=AiDecision.APPROVE,
            confidence=0.95,
            reason="Dev rejim: avtomatik tasdiqlandi",
            model="dev",
            detected_code=request.expected_code,
        )
