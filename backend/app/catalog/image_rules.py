from __future__ import annotations

MIN_PRODUCT_IMAGES = 3
MAX_PRODUCT_IMAGES = 15


def validate_product_image_count(image_count: int) -> None:
    if image_count < MIN_PRODUCT_IMAGES:
        raise ValueError(
            f"At least {MIN_PRODUCT_IMAGES} product images are required"
        )

    if image_count > MAX_PRODUCT_IMAGES:
        raise ValueError(
            f"Maximum {MAX_PRODUCT_IMAGES} product images are allowed"
        )
