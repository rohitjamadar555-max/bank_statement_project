
import re
import pandas as pd


CATEGORY_RULES = {
    "food": [
        "swiggy", "zomato", "restaurant", "food", "dominos",
        "pizza hut", "mcdonalds", "burger king", "kfc",
        "subway", "starbucks", "chaayos", "faasos", "biryani",
        "bakery", "ice cream", "food court"
    ],
    "shopping": [
        "amazon", "flipkart", "myntra", "ajio", "meesho",
        "snapdeal", "nykaa", "jiomart", "croma", "ikea",
        "decathlon", "shoppers stop", "westside"
    ],
    "travel": [
        "makemytrip", "goibibo", "cleartrip", "ixigo",
        "easemytrip", "yatra", "air india", "indigo",
        "redbus", "abhibus", "booking.com", "airbnb"
    ],
    "bills": [
    "bill payment", "postpaid bill", "prepaid recharge",
    "telephone bill", "dth", "recharge"
],
    "transfer": [
         "neft", "imps", "rtgs", "fund transfer",
        "money transfer", "self transfer", "account transfer",
        "personal transfer", "money received", "sent to",
        "received from"
    ],
    "entertainment": [
        "netflix", "spotify", "prime video", "hotstar",
        "disney+", "youtube premium", "sony liv", "zee5",
        "bookmyshow", "pvr", "inox", "steam", "playstation"
    ],
    "health": [
        "pharmacy", "doctor", "hospital", "clinic",
        "apollo pharmacy", "1mg", "pharmeasy", "netmeds",
        "medplus", "diagnostic", "pathology", "dental"
    ],
    "education": [
        "school", "college", "tuition", "course", "udemy",
        "coursera", "unacademy", "byju", "physicswallah",
        "exam fee", "university fee", "admission fee", "textbook",
          "book store", "bookshop", "stationery shop"
    ],
    "investment": [
        "mutual fund", "stocks", "bonds", "zerodha",
        "groww", "upstox", "angel one", "sip", "demat",
        "equity", "etf", "gold investment"
    ],
    "personal care": [
        "salon", "spa", "gym", "fitness", "cult.fit",
        "urban company", "barber", "haircut", "beauty",
        "cosmetics", "skincare", "laundry"
    ],
    "transportation": [
        "bus", "train", "taxi", "metro", "namma metro",
        "bmtc", "ksrtc", "rapido", "parking", "toll", "fastag","auto rickshaw", "ola", "uber", "cab"
    ],
    "utilities": [
    "electricity", "electricity bill", "water bill",
    "gas bill", "bescom", "bwssb",
    "indane gas", "hp gas", "bharat gas",
    "airtel broadband", "jiofiber", "act fibernet"
],
    "insurance": [
        "life insurance", "health insurance", "car insurance",
        "lic premium", "policy premium", "term insurance",
        "icici prudential", "hdfc life", "sbi life",
        "star health insurance"
    ],
    "loan": [
        "personal loan", "home loan", "car loan",
        "loan repayment", "loan emi", "emi payment",
        "education loan", "vehicle loan", "mortgage"
    ],
    "donation": [
        "charity", "donation", "fundraiser", "ngo",
        "relief fund", "crowdfunding", "charitable trust"
    ],
    "savings": [
        "savings account", "fixed deposit", "recurring deposit",
        "fd deposit", "rd deposit", "term deposit"
    ],
    "tax": [
        "income tax", "gst", "vat", "tax return",
        "advance tax", "professional tax", "tds", "tax payment"
    ],
    "income": [
        "salary", "bonus", "dividend", "interest",
        "payroll", "salary credit", "incentive", "commission received",
        "freelance payment", "freelance income", "client payment",
        "payment received", "salary received",
        "freelance payment",
        "freelance income",
        "client payment",
        "salary received",
    ],
    "groceries": [
        "bigbasket", "blinkit", "zepto", "instamart",
        "dmart", "more supermarket", "reliance fresh",
        "nature basket", "spencers", "star bazaar",
        "supermarket", "grocery", "vegetables", "fruits",
        "milk", "dairy", "provisions"
    ],
    "rent": [
        "house rent", "monthly rent", "flat rent",
        "apartment rent", "pg rent", "paying guest",
        "hostel rent", "landlord", "rental payment"
    ],
    "household": [
        "home cleaning", "house cleaning", "furniture",
        "home decor", "kitchen supplies", "utensils",
        "home appliances", "pest control", "plumber",
        "carpenter", "electrician service"
    ],
    "fuel": [
        "indian oil", "bharat petroleum", "hp petrol",
        "shell petrol", "petrol pump", "diesel", "petrol",
        "cng", "fuel station"
    ],
    "vehicle maintenance": [
        "car service", "bike service", "vehicle repair",
        "car repair", "bike repair", "tyre", "puncture repair",
        "engine oil", "automobile service"
    ],
    "mobile and internet": [
        "airtel", "jio", "vi recharge", "vodafone idea",
        "bsnl", "mobile bill", "sim recharge",
        "data pack", "internet pack", "fiber recharge"
    ],
    "bank charges": [
        "bank charges", "sms charges", "minimum balance",
        "account maintenance", "annual maintenance",
        "atm charges", "service charge", "processing fee",
        "cheque bounce", "transaction fee", "bank commission"
    ],
    "credit card": [
        "credit card bill", "card payment", "card settlement",
        "credit card outstanding", "card dues",
        "credit card repayment"
    ],
    "cash withdrawal": [
        "atm withdrawal", "cash withdrawal",
        "cash wdl", "atm wdl", "cash withdrawn"
    ],
    "government fees": [
        "passport fee", "driving licence",
        "vehicle registration", "rto payment",
        "government fee", "municipal tax",
        "property tax", "court fee", "challan payment"
    ],
    "legal services": [
        "lawyer fee", "advocate fee", "legal consultation",
        "notary", "court charges", "legal services"
    ],
    "pet care": [
        "pet clinic", "veterinary", "vet hospital",
        "pet food", "pet grooming", "pet vaccination",
        "dog food", "cat food"
    ],
    "childcare": [
        "daycare", "child care", "creche",
        "baby products", "baby food", "child tuition",
        "nursery fee", "playschool"
    ],
    "events and celebrations": [
        "event booking", "wedding expenses",
        "birthday party", "party hall", "banquet hall",
        "event management", "decoration", "catering",
        "marriage hall", "photography"
    ],
    "gifts": [
        "gift purchase", "gift card", "flower delivery",
        "fnp", "ferns n petals", "archies",
        "gift shop", "personalized gifts"
    ],
    "business expenses": [
        "office supplies", "business expense",
        "vendor payment", "inventory purchase",
        "raw materials", "business purchase",
        "commercial expense", "office rent"
    ],
    "software and cloud": [
        "microsoft 365", "google workspace", "adobe",
        "github", "openai", "chatgpt", "canva",
        "notion", "dropbox", "aws", "azure",
        "digitalocean", "hosting", "domain renewal"
    ],
    "professional services": [
        "consulting fee", "consultant", "accounting fee",
        "ca fee", "audit fee", "design service",
        "freelance service", "professional fee"
    ],
    "courier and delivery": [
        "dtdc", "blue dart", "bluedart", "delhivery",
        "india post", "fedex", "dhl", "ecom express",
        "courier charge", "shipping charge", "parcel"
    ],
    "accommodation": [
        "hotel booking", "hotel stay", "resort booking",
        "guest house", "lodging", "oyo", "treebo",
        "fab hotels", "taj hotels", "hostel booking"
    ],
    "parking and tolls": [
        "parking fee", "parking charges", "toll plaza",
        "highway toll", "fastag recharge", "parking ticket"
    ],
    "agriculture": [
        "fertilizer", "seeds purchase", "pesticide",
        "farm equipment", "agricultural supplies",
        "irrigation", "tractor repair"
    ],
    "foreign exchange": [
        "forex", "foreign currency", "currency exchange",
        "international transaction fee", "foreign exchange fee"
    ],
    "miscellaneous": [
        "miscellaneous", "other expense", "general expense"
    ],
}


def categorize_transaction(description: object) -> str:
    """Categorize a transaction using whole-word and phrase matching."""
    if pd.isna(description):
        return "uncategorized"

    text = str(description).casefold()
    text = re.sub(r"[^a-z0-9]+", " ", text).strip()

    for category, keywords in CATEGORY_RULES.items():
        for keyword in keywords:
            normalized_keyword = re.sub(
                r"[^a-z0-9]+", " ", keyword.casefold()
            ).strip()

            pattern = (
                r"(?<![a-z0-9])"
                + re.escape(normalized_keyword).replace(r"\ ", r"\s+")
                + r"(?![a-z0-9])"
            )

            if re.search(pattern, text):
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
