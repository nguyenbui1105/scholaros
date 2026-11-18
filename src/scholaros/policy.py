"""Per-opportunity AI writing and application policy gates."""
from enum import Enum

from .models import AIUsePolicy


class WritingAction(str, Enum):
    INTERVIEW = "interview"
    OUTLINE = "outline"
    EDIT = "edit"
    GENERATE_DRAFT = "generate_draft"


def writing_action_allowed(policy: AIUsePolicy, action: WritingAction) -> bool:
    """Conservative defaults: unknown or prohibited permits no AI writing assistance."""
    if policy is AIUsePolicy.ASSISTANCE_ALLOWED:
        return True
    if policy is AIUsePolicy.EDITING_ONLY:
        return action is WritingAction.EDIT
    return False


def submission_allowed(
    *, student_approved: bool, portal_permission_verified: bool, packet_verified: bool
) -> bool:
    """No autonomous-submit mode. Every action needs contemporaneous approval."""
    return student_approved and portal_permission_verified and packet_verified
