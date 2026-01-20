"""Industry mappings and lookup tables for company enrichment.

Contains NACE code to industry category mappings and other classification data.
"""

# NACE code (first 2 digits) to industry category mapping
NACE_INDUSTRY_MAPPING: dict[str, str] = {
    # Agriculture, forestry and fishing (01-03)
    "01": "Agriculture",
    "02": "Forestry",
    "03": "Fishing",
    # Mining and quarrying (05-09)
    "05": "Mining",
    "06": "Oil & Gas",
    "07": "Mining",
    "08": "Mining",
    "09": "Mining",
    # Manufacturing (10-33)
    "10": "Food & Beverages",
    "11": "Beverages",
    "12": "Tobacco",
    "13": "Textiles",
    "14": "Apparel",
    "15": "Leather",
    "16": "Wood",
    "17": "Paper",
    "18": "Printing",
    "19": "Petroleum",
    "20": "Chemicals",
    "21": "Pharmaceuticals",
    "22": "Rubber & Plastics",
    "23": "Non-metallic Minerals",
    "24": "Metals",
    "25": "Metal Products",
    "26": "Electronics",
    "27": "Electrical Equipment",
    "28": "Machinery",
    "29": "Motor Vehicles",
    "30": "Transport Equipment",
    "31": "Furniture",
    "32": "Other Manufacturing",
    "33": "Repair & Installation",
    # Utilities (35-39)
    "35": "Energy",
    "36": "Water",
    "37": "Sewerage",
    "38": "Waste Management",
    "39": "Remediation",
    # Construction (41-43)
    "41": "Construction",
    "42": "Civil Engineering",
    "43": "Specialized Construction",
    # Wholesale and retail trade (45-47)
    "45": "Motor Vehicle Trade",
    "46": "Wholesale Trade",
    "47": "Retail Trade",
    # Transportation and storage (49-53)
    "49": "Land Transport",
    "50": "Water Transport",
    "51": "Air Transport",
    "52": "Warehousing",
    "53": "Postal & Courier",
    # Accommodation and food service (55-56)
    "55": "Accommodation",
    "56": "Food Service",
    # Information and communication (58-63)
    "58": "Publishing",
    "59": "Motion Pictures",
    "60": "Broadcasting",
    "61": "Telecommunications",
    "62": "IT Services",
    "63": "Information Services",
    # Financial and insurance (64-66)
    "64": "Financial Services",
    "65": "Insurance",
    "66": "Auxiliary Financial",
    # Real estate (68)
    "68": "Real Estate",
    # Professional, scientific and technical (69-75)
    "69": "Legal & Accounting",
    "70": "Management Consulting",
    "71": "Architecture & Engineering",
    "72": "R&D",
    "73": "Advertising",
    "74": "Other Professional",
    "75": "Veterinary",
    # Administrative and support (77-82)
    "77": "Rental & Leasing",
    "78": "Employment",
    "79": "Travel Agencies",
    "80": "Security",
    "81": "Services to Buildings",
    "82": "Office Administration",
    # Public administration (84)
    "84": "Public Administration",
    # Education (85)
    "85": "Education",
    # Human health and social work (86-88)
    "86": "Human Health",
    "87": "Residential Care",
    "88": "Social Work",
    # Arts, entertainment and recreation (90-93)
    "90": "Creative Arts",
    "91": "Libraries & Archives",
    "92": "Gambling",
    "93": "Sports & Recreation",
    # Other service activities (94-96)
    "94": "Membership Organizations",
    "95": "Repair Services",
    "96": "Personal Services",
    # Activities of households (97-98)
    "97": "Household Activities",
    "98": "Household Activities",
    # Extraterritorial organizations (99)
    "99": "Extraterritorial",
}


def get_industry_category(nace_code: str | None) -> str:
    """Map NACE code to industry category.

    Args:
        nace_code: NACE code (e.g., "2221" for plastics manufacturing)

    Returns:
        Industry category string, or "unknown" if not found
    """
    if not nace_code:
        return "unknown"

    # Use first 2 digits for broad category
    category_code = nace_code[:2] if len(nace_code) >= 2 else nace_code
    return NACE_INDUSTRY_MAPPING.get(category_code, "unknown")
