import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import re
from io import BytesIO

from jinja2 import Environment, FileSystemLoader
from xhtml2pdf import pisa


def safe_filename(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    return name.strip().rstrip(".")


def count_adr(adr: float, month: int):
    k_adr = {
        1: 0.99, 2: 0.91, 3: 0.95, 4: 1, 5: 1.05, 6: 1.1,
        7: 1.09, 8: 1.07, 9: 1.07, 10: 1, 11: 0.92, 12: 1.1,
    }
    res = []
    for k_adr_val in k_adr.values():
        res.append((adr / k_adr[month]) * k_adr_val)
    return res


def count_occ(occ: float):
    k_occ = {
        1: 0.7, 2: 0.8, 3: 0.8, 4: 0.9, 5: 1.05, 6: 1.15,
        7: 1.25, 8: 1.2, 9: 1.05, 10: 0.95, 11: 0.8, 12: 0.95,
    }
    res = []
    for k_occ_val in k_occ.values():
        res.append(min(0.9, (occ / k_occ[1]) * k_occ_val))
    return res


def render_html_from_template(context: dict) -> str:
    """
    Рендерит template.html (Jinja2) в строку HTML.
    Шаблон лежит в корне проекта рядом с calculation.py.
    """
    base_dir = Path(__file__).resolve().parent
    env = Environment(loader=FileSystemLoader(str(base_dir)))
    # Если нужно использовать template-4.html — поменяй название здесь
    template = env.get_template("template.html")
    html = template.render(**context)
    return html


def html_to_pdf(html: str, output_path: Path) -> None:
    """
    Конвертирует HTML-строку в PDF с помощью xhtml2pdf.
    """
    result = BytesIO()
    pdf = pisa.CreatePDF(src=html, dest=result)  # encoding='utf-8' не обязателен
    if pdf.err:
        raise RuntimeError("Ошибка генерации PDF через xhtml2pdf")
    output_path.write_bytes(result.getvalue())


def generate_pdf_and_message(address: str, rooms: str, square: str, adr_real: list[float]):
    """
    Основная функция: считает показатели, рендерит HTML по template.html
    и конвертирует его в PDF через xhtml2pdf.
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

    # 3. Доход по месяцам (пока простая модель)
    base = Decimal("85000")
    step = Decimal("5000")
    real_net_revenue = [base + step * i for i in range(12)]
    real_net_revenue_sum_val = sum(real_net_revenue)
    real_net_revenue_sum = f"{real_net_revenue_sum_val:,}".replace(",", " ")

    optimistic_net_revenue_sum_val = (
        real_net_revenue_sum_val * Decimal("1.07")
    ).quantize(Decimal("1."), rounding=ROUND_HALF_UP)
    optimistic_net_revenue_sum = f"{optimistic_net_revenue_sum_val:,}".replace(",", " ")

    real_net_revenue_formatted = [
        f"{revenue:,}".replace(",", " ") for revenue in real_net_revenue
    ]

    # 4. Контекст под template.html / template-4.html
    context = {
        "address": address,
        "square": square,
        "rooms": rooms,
        "real_net_revenue": real_net_revenue_formatted,
        "real_net_revenue_sum": real_net_revenue_sum,
        "optimistic_net_revenue_sum": optimistic_net_revenue_sum,
        "real_avg_adr": real_avg_adr,
        "real_occ_avg": real_occ_avg,
    }

    # 5. Рендер HTML
    html = render_html_from_template(context)

    # 6. Генерация PDF
    base_dir = Path(__file__).resolve().parent
    filename = safe_filename(f"Расчет доход по {address}") + ".pdf"
    output_path = base_dir / filename
    html_to_pdf(html, output_path)

    # 7. Текст сообщения
    message = f"""Здравствуйте!

Меня зовут Ирина. Мы подготовили расчёт дохода по вашей квартире по адресу: {address}.

Предварительный годовой доход:
- {real_net_revenue_sum} ₽
- с потенциалом роста до {optimistic_net_revenue_sum} ₽

В файле приложены ожидаемые помесячные показатели. Пожалуйста, посмотрите их.
Если возникнут вопросы — можем созвониться или обсудить здесь, как вам будет удобнее.

Будем благодарны за вашу обратную связь."""
    return str(output_path), message
