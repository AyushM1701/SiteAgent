from agent.ecommerce_repair import build_shop_files, ground_shop_brief, shop_contract_missing


def test_disconnected_cart_is_detected():
    files = {
        "src/components/Products.tsx": "const [cart, setCart] = useState([])",
        "src/components/Cart.tsx": "const [cart, setCart] = useState([])",
    }
    assert shop_contract_missing(files, ["header", "products", "cart", "footer"])
    assert not shop_contract_missing(files, ["header", "products", "footer"])


def test_shop_repair_uses_only_supplied_catalog_and_shared_cart():
    files = build_shop_files({
        "products": [{"name": "Linen Table Runner", "price": "$48"}],
        "background_color": "#f6f1e7", "primary_color": "#203b2b",
    })
    products = files["src/components/Products.tsx"]
    cart = files["src/components/Cart.tsx"]
    assert "Linen Table Runner" in products and '"price": 48.0' in products
    assert "site-cart-updated" in products and "site-cart-updated" in cart
    assert "site-cart" in products and "site-cart" in cart
    assert "item.price * item.quantity" in cart
    assert "Shipping and payment are calculated" in cart
    assert "Fern & Fable" not in products
    assert "#f6f1e7" in files["src/components/Products.css"]


def test_shop_repair_recovers_catalog_missing_from_earlier_brief():
    grounded = ground_shop_brief(
        {"business_type": "ecommerce", "products": []},
        "Use warm cream and forest green. Products: Linen Table Runner at $48, and Ceramic Bud Vase at $38.",
    )
    assert len(grounded["products"]) == 2
    assert grounded["products"][1]["name"] == "Ceramic Bud Vase"
    assert grounded["background_color"] == "#f6f1e7"
    assert grounded["primary_color"] == "#203b2b"


def test_shop_repair_groups_products_when_categories_are_unsupplied():
    files = build_shop_files({"products": [
        {"name": "Linen Table Runner", "price": "$48"},
        {"name": "Oak Candle Holder", "price": "$32"},
        {"name": "Ceramic Bud Vase", "price": "$38"},
    ]})
    products = files["src/components/Products.tsx"]
    assert '"category": "Linens"' in products
    assert products.count('"category": "Decor"') == 2
