from services.listing_repository import (
    ListingRepository,
)


repository = ListingRepository()


# CREATE
# listing = repository.create(
#     title="Phòng trọ Thanh Xuân",
#     location="Thanh Xuân",
#     price=3500000,
#     address="Nguyễn Trãi, Thanh Xuân, Hà Nội",
#     area=25,
#     description="Phòng sạch đẹp, đầy đủ nội thất",
#     contact="0123456789",
# )

# print("Created:")
# print(listing)


# # READ
# listing = repository.get_by_id("R001")

# print("\nFound:")
# print(listing)


# # UPDATE
# listing = repository.update(
#     "R001",
#     price=3700000,
#     area=27,
# )

# print("\nUpdated:")
# print(listing)


# # READ ALL
# print("\nAll listings:")

# for listing in repository.get_all():
#     print(listing)


# DELETE
deleted = repository.delete("R002")
print("\nDeleted:", deleted)