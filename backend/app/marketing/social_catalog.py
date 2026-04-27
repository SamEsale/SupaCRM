from __future__ import annotations

from dataclasses import dataclass


SUPPORTED_SOCIAL_PROVIDERS: tuple[str, ...] = (
    "facebook",
    "instagram",
    "tiktok",
    "linkedin",
    "x",
)

SOCIAL_PROVIDER_DISPLAY_NAMES: dict[str, str] = {
    "facebook": "Facebook",
    "instagram": "Instagram",
    "tiktok": "TikTok",
    "linkedin": "LinkedIn",
    "x": "X",
}

SOCIAL_PROVIDER_REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "facebook": ("page_id", "access_token"),
    "instagram": ("account_id", "access_token"),
    "tiktok": ("account_id", "access_token"),
    "linkedin": ("account_id", "access_token"),
    "x": ("profile_id", "access_token"),
}


@dataclass(frozen=True, slots=True)
class SocialProviderCapability:
    provider: str
    display_name: str
    operator_summary: str


SOCIAL_PROVIDER_CAPABILITIES: dict[str, SocialProviderCapability] = {
    "facebook": SocialProviderCapability(
        provider="facebook",
        display_name="Facebook",
        operator_summary=(
            "Configuration only. Store the page and token details needed for future launch work "
            "without claiming OAuth or post publishing support."
        ),
    ),
    "instagram": SocialProviderCapability(
        provider="instagram",
        display_name="Instagram",
        operator_summary=(
            "Configuration only. Store business account identifiers and tokens without claiming "
            "publishing or inbox sync."
        ),
    ),
    "tiktok": SocialProviderCapability(
        provider="tiktok",
        display_name="TikTok",
        operator_summary=(
            "Configuration only. Operator settings are tenant-scoped, but TikTok publishing is not "
            "implemented in this slice."
        ),
    ),
    "linkedin": SocialProviderCapability(
        provider="linkedin",
        display_name="LinkedIn",
        operator_summary=(
            "Configuration only. Store organization settings without claiming OAuth completion or "
            "live posting."
        ),
    ),
    "x": SocialProviderCapability(
        provider="x",
        display_name="X",
        operator_summary=(
            "Configuration only. Account-level settings can be saved, but live posting and sync are "
            "not implemented."
        ),
    ),
}
