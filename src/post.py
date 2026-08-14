import argparse
from pathlib import Path

from services.content_loader import load_caption, load_images
from session_manager import get_session
from facebook.group_poster import post_to_groups


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
        nargs="+",
        required=True,
        help="One or more Facebook group URLs",
    )

    return parser.parse_args()


def main():
    args = parse_args()

    session_path = get_session(args.account)

    caption_file = Path(args.caption_file).resolve()
    images_folder = Path(args.images_folder).resolve()

    caption = load_caption(caption_file)
    images = load_images(images_folder)

    print("Post configuration")
    print("------------------")
    print(f"Account : {args.account}")
    print(f"Session : {session_path}")
    print(f"Group   : {args.group}")
    print(f"Caption : {caption_file}")
    print(f"Images  : {len(images)}")
    

    post_to_groups(
        session_path=session_path,
        group_urls=args.group,
        caption=caption,
        image_paths=images,
    )


if __name__ == "__main__":
    main()