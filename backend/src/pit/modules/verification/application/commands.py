from dataclasses import dataclass
from uuid import UUID

from pit.shared.application.messagebus import Command


@dataclass(frozen=True, kw_only=True)
class SubmitProof(Command):
    user_id: UUID
    participation_id: UUID
    task_key: str = "main"  # which task of today's plan this proves
    file_key: str | None = None  # object-storage key; the file was uploaded via a presigned URL
    text_note: str | None = None
    phash: str | None = None  # perceptual hash computed on upload, for duplicate detection


@dataclass(frozen=True, kw_only=True)
class VerifyProof(Command):
    """Run by a worker: pre-checks + AI verdict."""

    proof_id: UUID


@dataclass(frozen=True, kw_only=True)
class ReviewProof(Command):
    proof_id: UUID
    reviewer_id: UUID
    approved: bool
    note: str = ""
