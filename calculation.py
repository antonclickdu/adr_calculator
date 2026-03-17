import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import re

from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm


def safe_filename(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    return name.strip().rstrip(".")


def count_adr(adr: float, month: int):
    k_adr = {
        1: 0.99, 2: 0.91, 3: 0.95, 4: 1, 5: 1.05, 6: 1.1,
        7: 1.09, 8: 1.07, 9: 1.07, 10: 1, 11: 0.92, 12: 1.1
    }
    res = []
    for k_adr_val in k_adr.values():
        res.append((adr / k_adr[month]) * k_adr_val)
    return res


def count_occ(occ: float):
    k_occ = {
        1: 0.7, 2: 0.8, 3: 0.8, 4: 0.9, 5: 1.05, 6: 1.15,
        7: 1.25, 8: 1.2, 9: 1.05, 10: 0.95, 11: 0.8, 12: 0.95
    }
    res = []
    for k_occ_val in k_occ.values():
        res.append(min(0.9, (occ / k_occ[1]) * k_occ_val))
    return res


def generate_pdf_and_message(address: str, rooms: str, square: str, adr_real: list[float]):
    """
    Генерирует PDF с расчётом доходности (без wkhtmltopdf), используя
    те же данные, что и HTML-шаблон template-4.html.
    """
    # 1. Базовые расчёты
    month = datetime.date.today().month
    avg_adr = sum(adr_real) / len(adr_real)

    vals = {
        "address": address,
        "rooms": rooms,
        "square": square,
        "adr": [avg_adr, avg_adr],
        "occupancy": [0.53, 0.583],
        "month": month,
    }

    # 2. ADR и загрузка с учётом сезонности
    real_adr = count_adr(vals["adr"][0], month)
    real_avg_adr_val = Decimal(sum(real_adr) / len(real_adr)).quantize(
        Decimal("1."), rounding=ROUND_HALF_UP
    )
    real_avg_adr = f"{real_avg_adr_val:,}".replace(",", " ")

    real_occ = count_occ(vals["occupancy"][0])
    real_occ_avg_val = Decimal((sum(real_occ) / len(real_occ)) * 100).quantize(
        Decimal("1."), rounding=ROUND_HALF_UP
    )
    real_occ_avg = f"{real_occ_avg_val}"

    # 3. Доход по месяцам (простейшая модель, можно заменить своей)
    base = Decimal("85000")
    step = Decimal("5000")
    real_net_revenue = [base + step * i for i in range(12)]
    real_net_revenue_sum_val = sum(real_net_revenue)
    real_net_revenue_sum = f"{real_net_revenue_sum_val:,}".replace(",", "
