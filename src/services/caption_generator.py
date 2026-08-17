from models.listing import Listing


def format_price(price: int) -> str:
    return f"{price:,}".replace(",", ".")


def format_area(area: float) -> str:
    return f"{area:g}"


def generate_caption(listing: Listing) -> str:
    details: list[str] = []

    if listing.address.strip():
        details.append(
            f"📍 Địa chỉ: {listing.address.strip()}"
        )

    details.append(
        f"📌 Khu vực: {listing.location.strip()}"
    )
    details.append(
        f"💰 Giá: {format_price(listing.price)}đ/tháng"
    )

    if listing.area is not None:
        details.append(
            f"📐 Diện tích: "
            f"{format_area(listing.area)}m²"
        )

    blocks: list[str] = [
        listing.title.strip(),
        "\n".join(details),
    ]

    if listing.description.strip():
        blocks.append(listing.description.strip())

    if listing.contact.strip():
        blocks.append(
            f"☎️ Liên hệ: {listing.contact.strip()}"
        )

    return "\n\n".join(blocks).strip()
