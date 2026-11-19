"""Scholarship-specific AI writing and submission gates (fail closed)."""

from enum import StrEnum

from .models import AIUsePolicy


class WritingAction(StrEnum):
    INTERVIEW = "interview"
    OUTLINE = "outline"
    EDIT = "edit"
    GENERATE_DRAFT = "generate_draft"


class WritingMode(StrEnum):
    NONE = "none"
    FEEDBACK_ONLY = "feedback_only"
    OUTLINE_ONLY = "outline_only"
    FULL_DRAFT = "full_draft"


def writing_mode(policy: AIUsePolicy, *, disclosure_approved: bool = False) -> WritingMode:
    """Unknown and prohibited mean no AI writing. Disclosure requires a checkpoint."""
    if policy is AIUsePolicy.ASSISTANCE_ALLOWED:
        return WritingMode.FULL_DRAFT
    if policy is AIUsePolicy.DISCLOSE_REQUIRED:
        return WritingMode.FULL_DRAFT if disclosure_approved else WritingMode.OUTLINE_ONLY
    if policy is AIUsePolicy.EDITING_ONLY:
        return WritingMode.FEEDBACK_ONLY
    return WritingMode.NONE


def writing_action_allowed(
    policy: AIUsePolicy,
    action: WritingAction,
    *,
    disclosure_approved: bool = False,
) -> bool:
    mode = writing_mode(policy, disclosure_approved=disclosure_approved)
    if mode is WritingMode.FULL_DRAFT:
        return True
    if mode is WritingMode.OUTLINE_ONLY:
        return action in (WritingAction.OUTLINE, WritingAction.INTERVIEW)
    if mode is WritingMode.FEEDBACK_ONLY:
        return action is WritingAction.EDIT
    return False


def submission_allowed(
    *, student_approved: bool, portal_permission_verified: bool, packet_verified: bool
) -> bool:
    """No standing approval: approval must refer to the exact current packet."""
    return student_approved and portal_permission_verified and packet_verified
