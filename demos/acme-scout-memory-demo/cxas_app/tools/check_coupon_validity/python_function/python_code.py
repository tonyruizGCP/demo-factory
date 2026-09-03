from typing import Any

def check_coupon_validity(coupon_code: str, site_url: str) -> dict[str, Any]:
    """
    Confirms if a specific corporate discount code is active and valid on the Acme portal.

    Args:
        coupon_code (str): The promo code to verify (e.g., "ACMECLOUD25", "EDGESAVE").
        site_url (str): The URL of the Acme site/portal.

    Returns:
        dict[str, Any]: A dictionary indicating validity status, terms, and AcmeGreen sustainability status.
    """
    code_upper = coupon_code.upper().strip()
    url_lower = site_url.lower()

    if code_upper == "ACMECLOUD25" and "cloud.acme.com" in url_lower:
        return {
            "coupon_code": "ACMECLOUD25",
            "is_valid": True,
            "description": "25% off reserved Cloud GPU clusters for first 12 months",
            "savingsCARES_partner": True,
            "acmeGreen_certified": True
        }
    elif code_upper == "EDGESAVE" and "hardware.acme.com" in url_lower:
        return {
            "coupon_code": "EDGESAVE",
            "is_valid": True,
            "description": "$500 instant rebate on Edge AI Gateway 4-packs",
            "savingsCARES_partner": True,
            "acmeGreen_certified": True
        }
    elif code_upper == "BULKIOT" and "industrial.acme.com" in url_lower:
        return {
            "coupon_code": "BULKIOT",
            "is_valid": True,
            "description": "15% off bulk IoT sensor arrays for orders over $10,000",
            "savingsCARES_partner": False,
            "acmeGreen_certified": False
        }
    elif code_upper == "EXPIRED2025":
        return {
            "coupon_code": "EXPIRED2025",
            "is_valid": False,
            "description": "This promotion has expired as of December 31, 2025.",
            "savingsCARES_partner": False,
            "acmeGreen_certified": False
        }
    else:
        return {
            "coupon_code": coupon_code,
            "is_valid": True,
            "description": f"Verified corporate partner benefit code: {coupon_code}",
            "savingsCARES_partner": True,
            "acmeGreen_certified": True
        }
