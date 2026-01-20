"""Base feature extraction utilities.

Common helper functions for feature extraction across all enrichment types.
Provides reusable patterns for brackets, categories, and data completeness scoring.
"""

# TODO: expand this list
FREE_EMAIL_PROVIDERS = {
    "gmail.com",
    "yahoo.com",
    "hotmail.com",
    "outlook.com",
    "icloud.com",
    "mail.com",
    "protonmail.com",
    "aol.com",
    "zoho.com",
    "yandex.com",
    "gmx.com",
    "live.com",
    "msn.com",
    "inbox.com",
    "mail.ru",
    "proton.me",
    "tutanota.com",
    "tuta.com",
}


def get_employees_bracket(employees: float | None) -> str:
    """Categorize employee count into brackets."""

    if employees is None:
        return "unknown"
    if employees <= 9:
        return "1-9"  # micro
    elif employees <= 49:
        return "10-49"  # small
    elif employees <= 249:
        return "50-249"  # medium
    else:
        return "250+"  # large


def get_revenue_bracket(revenue: float | None) -> str:
    """Categorize revenue into brackets."""
    if revenue is None:
        return "unknown"
    if revenue < 250_000:
        return "<250K"  # micro
    elif revenue < 500_000:
        return "250K-500K"  # small
    elif revenue < 5_000_000:
        return "500K-5M"  # medium
    elif revenue < 50_000_000:
        return "5M-50M"  # large
    else:
        return "50M+"  # enterprise


def get_cash_flow_bracket(cash_flow: float | None) -> str:
    """Categorize cash flow into brackets."""
    return get_revenue_bracket(cash_flow)


def get_profit_before_tax_bracket(profit: float | None) -> str:
    """Categorize profit before tax into brackets."""
    return get_revenue_bracket(profit)


def get_profit_loss_bracket(profit: float | None) -> str:
    """Categorize profit/loss into brackets."""
    return get_revenue_bracket(profit)


def get_shareholders_funds_bracket(funds: float | None) -> str:
    """Categorize shareholders funds into brackets."""
    return get_revenue_bracket(funds)


def get_total_assets_bracket(assets: float | None) -> str:
    """Categorize total assets into brackets."""
    return get_revenue_bracket(assets)


def get_email_domain_type(domain: str | None) -> str:
    """
    Determine if email domain is from a free provider or company domain.

    Args:
        domain: Email domain (e.g., "gmail.com", "company.com")

    Returns:
        "free" if from free provider, "company" if company domain, "unknown" if None
    """
    if not domain:
        return "unknown"

    # Normalize domain (lowercase, remove www, extract base domain)
    domain_lower = domain.lower().strip()
    if domain_lower.startswith("www."):
        domain_lower = domain_lower[4:]
    if domain_lower.startswith("http://"):
        domain_lower = domain_lower[7:]
    if domain_lower.startswith("https://"):
        domain_lower = domain_lower[8:]

    # Extract base domain (e.g., "mail.google.com" -> "google.com")
    parts = domain_lower.split(".")
    if len(parts) >= 2:
        base_domain = ".".join(parts[-2:])
    else:
        base_domain = domain_lower

    if base_domain in FREE_EMAIL_PROVIDERS:
        return "free"
    return "company"
