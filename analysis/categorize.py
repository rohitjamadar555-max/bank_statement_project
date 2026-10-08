import pandas as pd


CATEGORY_RULES = {
    "food": ["swiggy", "zomato", "restaurant", "food"],
    "shopping": ["amazon", "flipkart", "myntra"],
    "travel": ["uber", "ola", "irctc", "flight"],
    "bills": ["electricity", "recharge", "broadband", "dth"],
    "transfer": ["upi", "neft", "imps", "rtgs"],
    "entertainment": ["netflix", "spotify", "prime video", "hotstar"],
    "health": ["pharmacy", "doctor", "hospital", "clinic"],
    "education": ["school", "college", "tuition", "course"],
    "investment": ["mutual fund", "stocks", "bonds", "savings"],
    "personal care": ["salon", "spa", "gym", "fitness"],
    "transportation": ["bus", "train", "taxi", "metro"],
    "utilities": ["water", "gas", "electricity", "internet"],
    "insurance": ["life insurance", "health insurance", "car insurance"],
    "loan": ["personal loan", "home loan", "car loan"],
    "donation": ["charity", "donation", "fundraiser"],
    "savings": ["savings account", "fixed deposit", "recurring deposit"],
    "tax": ["income tax", "gst", "vat", "tax return"],
    "income": ["salary", "bonus", "dividend", "interest"],
}


def categorize_transaction(description: object) -> str:
    """Choose a category by looking for a keyword in the description."""
    if pd.isna(description):
        return "uncategorized"

    text = str(description).casefold()

    for category, keywords in CATEGORY_RULES.items():
        if any(keyword.casefold() in text for keyword in keywords):
            return category

    return "uncategorized"


def add_categories(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of the transactions with a category column."""
    if "description" not in df.columns:
        raise ValueError("Cannot categorize transactions: 'description' is missing.")

    result = df.copy()
    result["category"] = result["description"].apply(categorize_transaction)
    return result


def uncategorized_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """Return uncategorized rows for review without changing the input."""
    if "category" not in df.columns:
        raise ValueError("Cannot find uncategorized rows: 'category' is missing.")

    return df.loc[df["category"].eq("uncategorized")].copy()