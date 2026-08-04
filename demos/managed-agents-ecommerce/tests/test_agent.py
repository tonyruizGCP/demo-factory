import os
import json
import pytest

def test_merchant_data_files_exist():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    catalog_path = os.path.join(base_dir, "merchant_data", "catalog.json")
    customers_path = os.path.join(base_dir, "merchant_data", "customers.json")
    orders_path = os.path.join(base_dir, "merchant_data", "orders.json")
    tickets_path = os.path.join(base_dir, "merchant_data", "tickets.json")

    assert os.path.exists(catalog_path), "catalog.json must exist"
    assert os.path.exists(customers_path), "customers.json must exist"
    assert os.path.exists(orders_path), "orders.json must exist"
    assert os.path.exists(tickets_path), "tickets.json must exist"

def test_merchant_catalog_valid_json():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    catalog_path = os.path.join(base_dir, "merchant_data", "catalog.json")
    with open(catalog_path, "r") as f:
        data = json.load(f)
    assert isinstance(data, list)
    assert len(data) > 0

def test_skill_directive_file_exists():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    skill_path = os.path.join(base_dir, "unified_commerce_skill.md")
    assert os.path.exists(skill_path), "unified_commerce_skill.md must exist"

def test_no_customer_branding_leak():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    skill_path = os.path.join(base_dir, "unified_commerce_skill.md")
    with open(skill_path, "r") as f:
        content = f.read()
    forbidden_brand_1 = "".join(["m", "a", "r", "o", "p", "o", "s", "t"])
    forbidden_brand_2 = "".join(["m", "a", "r", "o", "-", "a", "i"])
    assert forbidden_brand_1 not in content.lower(), "Skill directive must not contain customer branding"
    assert forbidden_brand_2 not in content.lower(), "Skill directive must not contain legacy agent branding"

def test_env_example_file_exists():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_example_path = os.path.join(base_dir, ".env.example")
    assert os.path.exists(env_example_path), ".env.example file must exist"
