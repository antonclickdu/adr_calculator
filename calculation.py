import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import re
import pdfkit
from jinja2 import Environment, FileSystemLoader

# ====== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ======

def safe_filename(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name)
    return name.strip().rstrip('.')

def count_adr(adr, month: int):
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

# ====== ГЛАВНАЯ ФУНКЦИЯ ======

def generate_pdf_and_message(address: str, rooms: str, square: str, adr_real: list[float]):
    """
    Генерирует PDF по шаблону template.html в корне репозитория
    и текст сообщения для владельца квартиры.
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

    # 2. ADR и загрузка с учётом сезонности (как в вашем коде)
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

    # 3. Доход по месяцам (сейчас — простая модель; подставите свою формулу)
    months = [
        "январь", "февраль", "март", "апрель", "май", "июнь",
        "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь",
    ]

    # пример: линейный рост, вы можете заменить на реальную формулу
    base = Decimal("85000")
    step = Decimal("5000")
    real_net_revenue = [base + step * i for i in range(12)]

    real_net_revenue_sum_val = sum(real_net_revenue)
    real_net_revenue_sum = f"{real_net_revenue_sum_val:,}".replace(",", " ")

    optimistic_net_revenue_sum_val = (real_net_revenue_sum_val * Decimal("1.07")).quantize(
        Decimal("1."), rounding=ROUND_HALF_UP
    )
    optimistic_net_revenue_sum = f"{optimistic_net_revenue_sum_val:,}".replace(",", " ")

    # В шаблон template.html, судя по содержанию, нужны:
    # address, square, rooms,
    # real_net_revenue (список из 12 значений),
    # real_net_revenue_sum, optimistic_net_revenue_sum,
    # real_avg_adr, real_occ_avg
    real_net_revenue_formatted = [
        f"{revenue:,}".replace(",", " ") for revenue in real_net_revenue
    ]

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

    # 4. Рендер HTML по template.html в корне проекта
    # Будем считать, что calculation.py лежит в корне рядом с template.html
    base_dir = Path(__file__).resolve().parent
    env = Environment(loader=FileSystemLoader(str(base_dir)))
    template = env.get_template("template.html")
    html = template.render(**context)

    # 5. Генерация PDF pdfkit’ом
    output_name = safe_filename(f"Расчет доход по {address}") + ".pdf"
    output_path = base_dir / output_name

    # Если wkhtmltopdf установлен нестандартно, сюда можно передать config
    pdfkit.from_string(html, str(output_path))

    # 6. Текст сообщения (оставляю ваш текст, только подставляю суммы)
    message = f"""Здравствуйте!

Меня зовут Ирина. Мы подготовили расчёт дохода по вашей квартире по адресу: {address}.

Предварительный годовой доход:
- {real_net_revenue_sum} ₽
- с потенциалом роста до {optimistic_net_revenue_sum} ₽

В файле приложены ожидаемые помесячные показатели. Пожалуйста, посмотрите их.
Если возникнут вопросы — можем созвониться или обсудить здесь, как вам будет удобнее.

Будем благодарны за вашу обратную связь."""
    return str(output_path), message
