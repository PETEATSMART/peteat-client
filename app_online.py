from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import sqlite3, os
import qrcode
from io import BytesIO

# -----------------------------
# CONFIG
# -----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "loyalty.db")

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# -----------------------------
# DB
# -----------------------------
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# -----------------------------
# AREA CLIENTE
# -----------------------------
@app.get("/card/{token}", response_class=HTMLResponse)
def public_card(request: Request, token: str):
    conn = db()
    cur = conn.cursor()

    customer = cur.execute(
        "SELECT * FROM customers WHERE public_token = ?",
        (token,)
    ).fetchone()

    if not customer:
        conn.close()
        return HTMLResponse("Cliente non trovato", status_code=404)

    card = cur.execute("""
        SELECT * FROM cards
        WHERE customer_id = ?
        LIMIT 1
    """, (customer["id"],)).fetchone()

    purchases = cur.execute("""
        SELECT * FROM purchases
        WHERE customer_id = ?
        ORDER BY created_at DESC
    """, (customer["id"],)).fetchall()

    cur.execute("""
        SELECT COALESCE(SUM(remaining_points), 0) AS balance
        FROM points_lots
        WHERE customer_id = ?
    """, (customer["id"],))

    balance_points = int(cur.fetchone()["balance"] or 0)

    customer_dict = dict(customer)
    customer_dict["points"] = balance_points

    conn.close()

    return templates.TemplateResponse(
        "card.html",
        {
            "request": request,
            "customer": customer_dict,
            "card": dict(card) if card else None,
            "purchases": [dict(p) for p in purchases],
        },
    )

# -----------------------------
# QR
# -----------------------------
@app.get("/qr")
def generate_qr(data: str):
    qr = qrcode.make(data)
    buf = BytesIO()
    qr.save(buf, format="PNG")
    return Response(content=buf.getvalue(), media_type="image/png")

# -----------------------------
# BARCODE
# -----------------------------
@app.get("/barcode")
def generate_barcode(data: str):
    import barcode
    from barcode.writer import ImageWriter

    CODE128 = barcode.get_barcode_class("code128")
    buf = BytesIO()
    barcode_img = CODE128(data, writer=ImageWriter())
    barcode_img.write(buf)

    return Response(content=buf.getvalue(), media_type="image/png")
