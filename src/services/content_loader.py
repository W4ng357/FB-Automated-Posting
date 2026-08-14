from pathlib import Path

SUPPORTED_IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
}

def load_images(images_folder: Path) -> list[Path]:
    if not images_folder.is_dir():
        raise NotADirectoryError(
            f"Images folder does not exist: {images_folder}"
        )

    images = sorted(
        image
        for image in images_folder.iterdir()
        if image.is_file()
        and image.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS
    )

    if not images:
        raise ValueError(
            f"No images found in: {images_folder}"
        )

    return images
    
def load_caption(caption_file: Path) -> str:
    if not caption_file.is_file():
        raise FileNotFoundError(
            f"Caption file not found: {caption_file}"
        )

    caption = caption_file.read_text(
        encoding="utf-8"
    ).strip()

    if not caption:
        raise ValueError(
            f"Caption file is empty: {caption_file}"
        )

    return caption

