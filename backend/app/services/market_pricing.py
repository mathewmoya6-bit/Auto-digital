from statistics import median

from services.supabase_client import get_supabase


supabase = get_supabase()


def save_market_listing(listing):
    """
    Prevent duplicates.
    """

    existing = (
        supabase.table("market_listings")
        .select("id")
        .eq("listing_id", listing["listing_id"])
        .execute()
    )

    if existing.data:

        (
            supabase.table("market_listings")
            .update(listing)
            .eq("listing_id", listing["listing_id"])
            .execute()
        )

    else:

        (
            supabase.table("market_listings")
            .insert(listing)
            .execute()
        )


def calculate_market_price(make, model, year):

    result = (
        supabase.table("market_listings")
        .select("price")
        .eq("make", make)
        .eq("model", model)
        .eq("year", year)
        .execute()
    )

    prices = [
        float(item["price"])
        for item in result.data
        if item["price"] is not None
    ]

    if not prices:
        return None

    market = {
        "make": make,
        "model": model,
        "year": year,
        "average_price": sum(prices) / len(prices),
        "lowest_price": min(prices),
        "highest_price": max(prices),
        "median_price": median(prices),
        "listing_count": len(prices)
    }

    return market
