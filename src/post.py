import argparse

from facebook.group_poster import post_to_groups
from models.group_target import GroupTarget
from services.listing_service import ListingService
from services.post_summary import post_summary
from session_manager import get_session


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Post a saved rental listing to "
            "Facebook groups."
        )
    )

    parser.add_argument(
        "account",
        help="Browser session account name, e.g. accQuan"
    )

    parser.add_argument(
        "listing_id",
        help="Saved listing ID, e.g. R001",
    )

    parser.add_argument(
        "--group",
        action="append",
        nargs=2,
        metavar=("URL", "COUNT"),
        required=True,
        help="Facebook group URL followed by target post count",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    session_path = get_session(args.account)
    listing_service = ListingService()

    listing = listing_service.get_by_id(
        args.listing_id
    )

    if listing is None:
        raise KeyError(
            f"Listing not found: {args.listing_id}"
        )

    caption, images = (
        listing_service.prepare_for_posting(
            args.listing_id
        )
    )

    group_targets = [
        GroupTarget(
            url=url,
            target_count=int(count),
        )
        for url, count in args.group
    ]

    print("Post configuration")
    print("------------------")
    print(f"Account : {args.account}")
    print(f"Listing : {listing.id}")
    print(f"Title   : {listing.title}")
    print(f"Images  : {len(images)}")
    print("Groups  :")

    for group in group_targets:
        print(
            f"  - {group.url} "
            f"(target: {group.target_count})"
        )

    results = post_to_groups(
        session_path=session_path,
        group_targets=group_targets,
        caption=caption,
        image_paths=images,
    )

    post_summary(results)


if __name__ == "__main__":
    main()
