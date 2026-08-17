from pathlib import Path

from services.listing_asset_manager import (
    ListingAssetManager,
)


manager = ListingAssetManager()


# CREATE FOLDER
folder = manager.create_listing_folder(
    "R001"
)

print("Images folder:")
print(folder)


# ADD
images = manager.add_images(
    "R001",
    [
        Path("/path/to/image1.jpg"),
        Path("/path/to/image2.jpg"),
    ],
)

print("\nImported:")

for image in images:
    print(image)


# READ
print("\nCurrent images:")

for image in manager.get_images("R001"):
    print(image)


# DELETE ONE
# manager.delete_image(
#     "R001",
#     "001.jpg",
# )


# DELETE ALL
# count = manager.clear_images("R001")
# print("Deleted:", count)