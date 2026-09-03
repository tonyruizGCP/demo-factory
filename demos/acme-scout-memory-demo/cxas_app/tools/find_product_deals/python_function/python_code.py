from typing import Any

def find_product_deals(query: str, image_metadata: dict | None = None) -> dict[str, Any]:
    """
    Searches for enterprise hardware, cloud infrastructure, and procurement deals in the Acme catalog.

    Args:
        query (str): A text query describing the product or solution (e.g., "Edge AI Gateway", "Cloud Compute Cluster").
        image_metadata (dict | None): Optional metadata extracted from an uploaded blueprint or equipment image.

    Returns:
        dict[str, Any]: A dictionary containing details of the verified enterprise solution, or an indication if no deal is found.
    """
    product_name = ""
    if image_metadata and "model" in image_metadata and "brand" in image_metadata:
        product_name = f"{image_metadata["brand"]} {image_metadata["model"]}"
    elif query:
        product_name = query

    product_lower = product_name.lower()

    if "edge" in product_lower or "gateway" in product_lower:
        return {
            "product_name": "Acme Edge AI Gateway (Gen 4)",
            "retailer": "Acme Hardware Labs",
            "offer": "$500 off multi-pack enterprise deployments",
            "savingsCARES_partner": True,
            "acmeGreen_certified": True,
            "specifications": "Dual TPU Accelerators, IP67 ruggedized, 45W peak power",
            "link": "https://hardware.acme.com/edge-ai-gateway"
        }
    elif "cloud" in product_lower or "compute" in product_lower or "gpu" in product_lower or "cluster" in product_lower:
        return {
            "product_name": "Acme Cloud Dedicated Compute Cluster",
            "retailer": "Acme Cloud Systems",
            "offer": "25% off reserved annual instances + 100TB free egress",
            "savingsCARES_partner": True,
            "acmeGreen_certified": True,
            "specifications": "NVIDIA H100/B200 nodes, liquid cooling, 100% renewable powered",
            "link": "https://cloud.acme.com/compute-clusters"
        }
    elif "sensor" in product_lower or "iot" in product_lower or "industrial" in product_lower:
        return {
            "product_name": "Acme Industrial IoT High-Precision Sensor Array",
            "retailer": "Acme Industrial",
            "offer": "15% discount on bulk facility deployments (>50 units)",
            "savingsCARES_partner": False,
            "acmeGreen_certified": False,
            "specifications": "Sub-millisecond latency, BLE/LoRaWAN, 10-year battery life",
            "link": "https://industrial.acme.com/sensors"
        }
    elif "quantum" in product_lower:
        return {
            "product_name": "Acme Quantum Hybrid Simulator Appliance",
            "retailer": "Acme Advanced Tech",
            "offer": "Executive evaluation pilot program with zero upfront licensing",
            "savingsCARES_partner": True,
            "acmeGreen_certified": True,
            "specifications": "128-qubit emulation matrix, cryogenic interface bridge",
            "link": "https://advanced.acme.com/quantum"
        }
    else:
        return {"product_name": product_name if product_name else "Unknown Solution", "offer": "No active promotional deals found. Standard enterprise pricing applies."}
