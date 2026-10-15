"""Grounded, functional storefront fallback for disconnected generated shop sections."""

from __future__ import annotations

import json
import re
from typing import Any


def _category_for_name(name: str) -> str:
    """Use a broad product grouping when no catalog category was supplied."""
    lower = name.lower()
    groups = (
        (r"\b(?:runner|napkin|tablecloth|placemat|towel)\b", "Linens"),
        (r"\b(?:vase|candle|holder|planter|mirror|frame)\b", "Decor"),
        (r"\b(?:shirt|jacket|dress|sweater|trouser|jeans)\b", "Apparel"),
        (r"\b(?:shoe|boot|sneaker|sandal)\b", "Footwear"),
        (r"\b(?:book|journal|notebook)\b", "Books & stationery"),
    )
    return next((category for pattern, category in groups if re.search(pattern, lower)), "Other products")


def ground_shop_brief(brief: dict[str, Any], prompt: str) -> dict[str, Any]:
    """Recover explicit catalog facts when an earlier brief omitted them."""
    grounded = dict(brief)
    if not grounded.get("products"):
        catalog = re.search(r"\b(?:products|catalog|items)\s*:\s*([^\n.]+)", prompt, re.I)
        products: list[dict[str, str]] = []
        if catalog:
            for part in re.split(r",\s*(?:and\s+)?|\s+and\s+", catalog.group(1)):
                item = re.sub(r"^and\s+", "", part.strip(), flags=re.I)
                match = re.fullmatch(r"([A-Za-z][A-Za-z0-9 '&-]{1,60}?)\s+(?:at|for|[-–:])\s*(\$\d+(?:\.\d{1,2})?)", item)
                if match:
                    products.append({"name": match.group(1).strip(), "price": match.group(2)})
        grounded["products"] = products
    if re.search(r"\bwarm cream\b", prompt, re.I):
        grounded["background_color"] = "#f6f1e7"
    if re.search(r"\bforest green\b", prompt, re.I):
        grounded["primary_color"] = "#203b2b"
    return grounded


def shop_contract_missing(files: dict[str, str], sections: list[str]) -> bool:
    if not {"products", "cart"}.issubset({section.lower() for section in sections}):
        return False
    products = files.get("src/components/Products.tsx", "")
    cart = files.get("src/components/Cart.tsx", "")
    if not products or not cart:
        return False
    product_contract = all(token in products for token in ("site-cart", "site-cart-updated", "localStorage"))
    cart_contract = all(token in cart for token in ("site-cart", "site-cart-updated", "localStorage", "quantity"))
    false_checkout = bool(re.search(r"alert\s*\([^)]*\b(?:order|payment)\b[^)]*\b(?:placed|confirmed|processed|shipped)\b", cart, re.I))
    return not (product_contract and cart_contract) or false_checkout


def build_shop_files(brief: dict[str, Any]) -> dict[str, str]:
    products: list[dict[str, Any]] = []
    for index, item in enumerate(brief.get("products") or []):
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        price_text = str(item.get("price", "")).strip()
        match = re.fullmatch(r"\$(\d+(?:\.\d{1,2})?)", price_text)
        if not name or not match:
            continue
        products.append({
            "id": f"product-{index + 1}", "name": name,
            "price": float(match.group(1)),
            "category": str(item.get("category") or _category_for_name(name)),
        })

    product_json = json.dumps(products, ensure_ascii=True)
    products_tsx = r'''import React, { useState } from 'react';
import './Products.css';

type ShopProduct = { id: string; name: string; price: number; category: string };
type CartItem = ShopProduct & { quantity: number };
const PRODUCTS: ShopProduct[] = __PRODUCTS__;
const money = (value: number) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);

function readCart(): CartItem[] {
  try {
    const parsed: unknown = JSON.parse(localStorage.getItem('site-cart') || '[]');
    return Array.isArray(parsed) ? parsed as CartItem[] : [];
  } catch { return []; }
}

export function Products() {
  const [category, setCategory] = useState('All');
  const categories = ['All', ...Array.from(new Set(PRODUCTS.map((product) => product.category)))];
  const visible = category === 'All' ? PRODUCTS : PRODUCTS.filter((product) => product.category === category);

  const addToCart = (product: ShopProduct) => {
    const current = readCart();
    const existing = current.find((item) => item.id === product.id);
    const next = existing
      ? current.map((item) => item.id === product.id ? { ...item, quantity: item.quantity + 1 } : item)
      : [...current, { ...product, quantity: 1 }];
    try { localStorage.setItem('site-cart', JSON.stringify(next)); } catch { /* storage unavailable */ }
    window.dispatchEvent(new Event('site-cart-updated'));
  };

  return <section id="products" className="site-products" data-repaired="shop-contract">
    <div className="site-products__inner">
      <div className="site-products__intro"><span>The collection</span><h2>Explore the collection</h2></div>
      {categories.length > 2 && <div className="site-products__filters" aria-label="Filter products">
        {categories.map((option) => <button key={option} type="button" aria-pressed={category === option}
          onClick={() => setCategory(option)}>{option}</button>)}
      </div>}
      {PRODUCTS.length === 0 ? <p className="site-products__empty">Catalog details are coming soon.</p> :
        <div className="site-products__grid">{visible.map((product) => <article className="site-products__card" key={product.id}>
          <div className="site-products__visual" aria-hidden="true">{product.name.slice(0, 1)}</div>
          <div className="site-products__meta"><h3>{product.name}</h3><span className="site-products__price">{money(product.price)}</span></div>
          <button className="site-products__button" type="button" onClick={() => addToCart(product)}
            aria-label={`Add ${product.name} to cart`}>Add to cart</button>
        </article>)}</div>}
    </div>
  </section>;
}

export default Products;
'''.replace("__PRODUCTS__", product_json)

    cart_tsx = r'''import React, { useEffect, useState } from 'react';
import './Cart.css';

type CartItem = { id: string; name: string; price: number; category: string; quantity: number };
const money = (value: number) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);

function readCart(): CartItem[] {
  try {
    const parsed: unknown = JSON.parse(localStorage.getItem('site-cart') || '[]');
    return Array.isArray(parsed) ? parsed as CartItem[] : [];
  } catch { return []; }
}

export function Cart() {
  const [items, setItems] = useState<CartItem[]>([]);
  useEffect(() => {
    const sync = () => setItems(readCart());
    sync();
    window.addEventListener('site-cart-updated', sync);
    window.addEventListener('storage', sync);
    return () => { window.removeEventListener('site-cart-updated', sync); window.removeEventListener('storage', sync); };
  }, []);

  const writeCart = (next: CartItem[]) => {
    setItems(next);
    try { localStorage.setItem('site-cart', JSON.stringify(next)); } catch { /* storage unavailable */ }
    window.dispatchEvent(new Event('site-cart-updated'));
  };
  const changeQuantity = (id: string, amount: number) =>
    writeCart(items.map((item) => item.id === id ? { ...item, quantity: Math.max(1, item.quantity + amount) } : item));
  const remove = (id: string) => writeCart(items.filter((item) => item.id !== id));
  const subtotal = items.reduce((sum, item) => sum + item.price * item.quantity, 0);

  return <section id="cart" className="site-cart" data-repaired="shop-contract">
    <div className="site-cart__inner">
      <div className="site-cart__intro"><span>Your selection</span><h2>Shopping cart</h2></div>
      {items.length === 0 ? <div className="site-cart__empty"><p>Your cart is empty.</p><a href="#products">Explore products</a></div> :
        <div className="site-cart__layout"><ul className="site-cart__items">{items.map((item) => <li key={item.id} className="site-cart__item">
          <div><h3>{item.name}</h3><p>{money(item.price)} each</p></div>
          <div className="site-cart__controls">
            <button type="button" aria-label={`Decrease quantity of ${item.name}`} onClick={() => changeQuantity(item.id, -1)} disabled={item.quantity <= 1}>−</button>
            <output aria-label={`${item.name} quantity`}>{item.quantity}</output>
            <button type="button" aria-label={`Increase quantity of ${item.name}`} onClick={() => changeQuantity(item.id, 1)}>+</button>
            <button type="button" className="site-cart__remove" onClick={() => remove(item.id)}>Remove</button>
          </div>
        </li>)}</ul>
        <aside className="site-cart__summary"><h3>Order summary</h3><div><span>Subtotal</span><strong>{money(subtotal)}</strong></div>
          <p>Shipping and payment are calculated when a checkout service is connected.</p>
        </aside></div>}
    </div>
  </section>;
}

export default Cart;
'''

    products_css = '''.site-products { background: __BG__; color: __PRIMARY__; padding: clamp(3rem, 7vw, 6rem) 1.25rem; }
.site-products__inner { max-width: 1200px; margin: 0 auto; }
.site-products__intro span { text-transform: uppercase; letter-spacing: .15em; font-size: .75rem; }
.site-products__intro h2 { font-size: clamp(2rem, 4vw, 3.5rem); margin: .5rem 0 2rem; }
.site-products__filters { display: flex; gap: .5rem; flex-wrap: wrap; margin-bottom: 2rem; }
.site-products__filters button { border: 1px solid currentColor; border-radius: 999px; background: transparent; color: inherit; padding: .55rem 1rem; cursor: pointer; }
.site-products__filters button[aria-pressed="true"] { background: __PRIMARY__; color: __BG__; }
.site-products__grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 240px), 1fr)); gap: 1.5rem; }
.site-products__card { background: #fff; border: 1px solid rgba(0,0,0,.12); border-radius: 1rem; overflow: hidden; display: flex; flex-direction: column; }
.site-products__visual { height: 190px; display: grid; place-items: center; background: linear-gradient(135deg, #eee6d8, #d9cbb7); color: __PRIMARY__; font-size: 4rem; font-family: Georgia, serif; }
.site-products__meta { padding: 1.25rem 1.25rem .5rem; display: flex; justify-content: space-between; gap: 1rem; align-items: baseline; }
.site-products__meta h3 { font-size: 1.1rem; margin: 0; }
.site-products__price { white-space: nowrap; font-weight: 700; }
.site-products__button { margin: auto 1.25rem 1.25rem; border: 0; border-radius: .5rem; background: __PRIMARY__; color: #fff; padding: .8rem 1rem; cursor: pointer; }
.site-products__empty { padding: 2rem; border: 1px dashed currentColor; border-radius: .75rem; }
.site-products button:focus-visible { outline: 3px solid __PRIMARY__; outline-offset: 3px; }
@media (prefers-reduced-motion: reduce) { .site-products *, .site-products *::before, .site-products *::after { animation: none !important; transition: none !important; } }
'''
    cart_css = '''.site-cart { background: #fff; color: __PRIMARY__; padding: clamp(3rem, 7vw, 6rem) 1.25rem; }
.site-cart__inner { max-width: 1200px; margin: 0 auto; }
.site-cart__intro span { text-transform: uppercase; letter-spacing: .15em; font-size: .75rem; }
.site-cart__intro h2 { font-size: clamp(2rem, 4vw, 3.5rem); margin: .5rem 0 2rem; }
.site-cart__layout { display: grid; grid-template-columns: minmax(0, 2fr) minmax(250px, 1fr); gap: 2rem; align-items: start; }
.site-cart__items { list-style: none; margin: 0; padding: 0; }
.site-cart__item { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem; padding: 1.25rem 0; border-bottom: 1px solid #ddd; }
.site-cart__item h3 { margin: 0 0 .3rem; font-size: 1.1rem; }
.site-cart__item p { margin: 0; opacity: .7; }
.site-cart__controls { display: flex; gap: .5rem; align-items: center; }
.site-cart__controls button { background: transparent; border: 1px solid currentColor; border-radius: .4rem; min-width: 2rem; min-height: 2rem; cursor: pointer; }
.site-cart__controls button:disabled { opacity: .4; cursor: not-allowed; }
.site-cart__remove { padding: 0 .6rem; }
.site-cart__summary { background: __BG__; padding: 1.5rem; border-radius: .75rem; }
.site-cart__summary h3 { margin-top: 0; }
.site-cart__summary div { display: flex; justify-content: space-between; gap: 1rem; font-size: 1.2rem; }
.site-cart__summary p { font-size: .85rem; line-height: 1.5; opacity: .75; }
.site-cart__empty { border: 1px dashed currentColor; border-radius: .75rem; padding: 2rem; }
.site-cart__empty a { color: inherit; text-decoration: underline; }
.site-cart button:focus-visible, .site-cart a:focus-visible { outline: 3px solid __PRIMARY__; outline-offset: 3px; }
@media (max-width: 700px) { .site-cart__layout { grid-template-columns: 1fr; } }
@media (prefers-reduced-motion: reduce) { .site-cart *, .site-cart *::before, .site-cart *::after { animation: none !important; transition: none !important; } }
'''
    def safe_color(value: object, fallback: str) -> str:
        text = str(value or "")
        return text if re.fullmatch(r"#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?", text) else fallback

    bg = safe_color(brief.get("background_color"), "#f6f1e7")
    primary = safe_color(brief.get("primary_color"), "#203b2b")
    return {
        "src/components/Products.tsx": products_tsx,
        "src/components/Products.css": products_css.replace("__BG__", bg).replace("__PRIMARY__", primary),
        "src/components/Cart.tsx": cart_tsx,
        "src/components/Cart.css": cart_css.replace("__BG__", bg).replace("__PRIMARY__", primary),
    }
