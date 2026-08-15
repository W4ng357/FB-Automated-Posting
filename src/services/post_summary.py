from models.post_result import PostResult


def post_summary(results: list[PostResult]) -> None:
    print("\n")
    print("=" * 50)
    print("POST SUMMARY")
    print("=" * 50)

    if not results:
        print("No post attempts were made.")
        print("=" * 50)
        return

    success_count = 0
    failed_count = 0

    for index, result in enumerate(results, start=1):
        group_name = result.group_name or "Unknown Group"

        print(f"\n[{index}] {group_name}")
        print(f"    Group URL : {result.group_url}")

        if result.success:
            success_count += 1

            print("    Status    : ✓ SUCCESS")

            if result.post_url:
                print(f"    Post URL  : {result.post_url}")
            else:
                print("    Post URL  : Unavailable")

        else:
            failed_count += 1

            print("    Status    : ✗ FAILED")
            print(
                f"    Error     : "
                f"{result.error or 'Unknown error'}"
            )

    print("\n" + "-" * 50)
    print(f"Total attempts : {len(results)}")
    print(f"Successful     : {success_count}")
    print(f"Failed         : {failed_count}")
    print("=" * 50)