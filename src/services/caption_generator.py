from models.listing import Listing


def format_price(price: int, unit: str = "TR") -> str:
    millions, remainder = divmod(price, 1_000_000)
    clean_unit = unit.strip() if unit else "TR"
    sep = " " if clean_unit.lower() in {"triệu", "trieu", "đồng", "dong", "vnd", "vnđ"} else ""

    if remainder == 0:
        return f"{millions}{sep}{clean_unit}"

    decimal_part = f"{remainder:06d}".rstrip("0")
    return f"{millions},{decimal_part}{sep}{clean_unit}"


def format_area(area: float) -> str:
    return f"{area:g}"


def generate_caption(listing: Listing) -> str:
    details: list[str] = []

    address = listing.address.strip() or listing.location.strip()
    if address:
        details.append(
            f"📍 Địa chỉ: {address}"
        )
    unit = getattr(listing, "price_unit", "TR") or "TR"
    details.append(
        f"💰 Giá: {format_price(listing.price, unit)}/tháng"
    )

    if listing.area is not None:
        details.append(
            f"📐 Diện tích: "
            f"{format_area(listing.area)}m²"
        )

    blocks: list[str] = []
    if listing.title.strip():
        blocks.append(listing.title.strip())
    blocks.append("\n".join(details))

    if listing.description.strip():
        blocks.append(listing.description.strip())

    if listing.contact.strip():
        blocks.append(
            f"☎️ Liên hệ: {listing.contact.strip()}"
        )

    return "\n\n".join(blocks).strip()
