from models.listing import Listing


def format_price(price: int) -> str:
    millions, remainder = divmod(price, 1_000_000)
    if remainder == 0:
        return f"{millions}tr"

    decimal_part = f"{remainder:06d}".rstrip("0")
    return f"{millions},{decimal_part}tr"


def format_area(area: float) -> str:
    return f"{area:g}"


def generate_caption(listing: Listing) -> str:
    details: list[str] = []

    address = listing.address.strip() or listing.location.strip()
    if address:
        details.append(
            f"📍 Địa chỉ: {address}"
        )
    details.append(
        f"💰 Giá: {format_price(listing.price)}/tháng"
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
