import argparse
from pathlib import Path

from models.group_target import GroupTarget
from services.content_loader import load_caption, load_images
from session_manager import get_session
from facebook.group_poster import post_to_groups
from services.post_summary import post_summary

def parse_args():
    parser = argparse.ArgumentParser(
        description="Post text and images to a Facebook group."
    )

    parser.add_argument(
        "account",
        help="Browser session account name, e.g. accQuan"
    )

    parser.add_argument(
        "caption_file",
        help="Path to the caption text file"
    )

    parser.add_argument(
        "images_folder",
        help="Path to the folder containing images"
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


def main():
    args = parse_args()

    session_path = get_session(args.account)

    caption_file = Path(args.caption_file).resolve()
    images_folder = Path(args.images_folder).resolve()

    caption = load_caption(caption_file)
    images = load_images(images_folder)
    
    group_targets = [
    GroupTarget(
        url=url,
        target_count=int(count),
        )
    for url, count in args.group
    ]
    # print(args.group)
    print("Post configuration")
    print("------------------")
    print(f"Account : {args.account}")
    print(f"Session : {session_path}")
    print(f"Caption : {caption_file}")
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