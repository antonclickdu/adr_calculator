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


# коэффициенты и словари — как в sample-1.3.ipynb
k_adr = {
    1: 0.99,
    2: 0.91,
    3: 0.95,
    4: 1,
    5: 1.05,
    6: 1.1,
    7: 1.09,
    8: 1.07,
    9: 1.07,
    10: 1,
    11: 0.92,
    12: 1.1,
}

k_occ = {
    1: 0.7,
    2: 0.8,
    3: 0.8,
    4: 0.9,
    5: 1.05,
    6: 1.15,
    7: 1.25,
    8: 1.2,
    9: 1.05,
    10: 0.95,
    11: 0.8,
    12: 0.95,
}

days_in_month = {
    1: 31,
    2: 28,
    3: 31,
    4: 30,
    5: 31,
    6: 30,
    7: 31,
    8: 31,
    9: 30,
    10: 31,
    11: 30,
    12: 31,
}

return_rate = {
    1: 0,
    2: 0,
    3: 0,
    4: 0,
    5: 0,
    6: 0,
    7: 0.05,
    8: 0.05,
    9: 0.05,
    10: 0.05,
    11: 0.05,
    12: 0.05,
}

adr_net_ota_percent = 0.15
adr_net_dc_percent = 0.10


def count_adr(adr: float, month: int):
    res = []
    for k_adr_val in k_adr.values():
        res.append((adr / k_adr[month]) * k_adr_val)
    return res


def count_adr_net_ota(adr_list):
    res = []
    for adr in adr_list:
        res.append(adr * (1 - adr_net_ota_percent))
    return res


def count_adr_net_los(adr_list, adr_net_ota_list):
    res = []
    for month_idx, (adr, adr_net_ota) in enumerate(zip(adr_list, adr_net_ota_list)):
        m = month_idx + 1
        res.append(
            ((1 - return_rate[m]) * adr_net_ota)
            + (return_rate[m]) * adr
        )
    return res


def count_adr_net_dc(adr_net_los_list):
    res = []
    for adr_net_los in adr_net_los_list:
        res.append(adr_net_los * (1 - adr_net_dc_percent))
    return res


def count_occ(occ: float):
    res = []
    for k_occ_val in k_occ.values():
        res.append(min(0.9, (occ / k_occ[1]) * k_occ_val))
    return res


def count_net_revenue(adr_net_dc_list, occ_list):
    res = []
    for month_idx, (adr_net_dc, occ) in enumerate(zip(adr_net_dc_list, occ_list)):
        m = month_idx + 1
        val = Decimal(
            days_in_month[m] * adr_net_dc * occ
        ).quantize(Decimal("1."), rounding=ROUND_HALF_UP)
        res.append(val)
    return res


def generate_pdf_and_message(
    address: str,
    rooms: str,
    square: str,
    adr_real: list[float],
    manager_name: str,
):
    """
    Полный расчёт по логике sample-1.3.ipynb + генерация PDF через ReportLab.
    """
    # 1. Подготовка данных как в ноутбуке
    month = datetime.date.today().month

    # adr_real — список цен конкурентов
    adr_optimistic = adr_real[:]  # в ноутбуке adr_optimistic = adr_real

    occ_real_list = [0.53]  # как в примере
    occ_optimistic = sum(occ_real_list) * 1.1

    avg_real_adr = sum(adr_real) / len(adr_real)
    avg_opt_adr = sum(adr_optimistic) / len(adr_real)

    vals = {
        "address": address,
        "rooms": rooms,
        "square": square,
    }
    vals.setdefault("adr", [avg_real_adr, avg_opt_adr])
    vals.setdefault(
        "occupancy",
        [sum(occ_real_list) / len(occ_real_list), occ_optimistic / len(occ_real_list)],
    )
    vals.setdefault("month", month)

    # 2. Реальный сценарий
    real_adr = count_adr(vals["adr"][0], vals["month"])
    real_avg_adr_val = Decimal(sum(real_adr) / len(real_adr)).quantize(
        Decimal("1."), rounding=ROUND_HALF_UP
    )
    real_avg_adr = f"{real_avg_adr_val:,}".replace(",", " ")

    real_adr_net_ota = count_adr_net_ota(real_adr)
    real_adr_net_los = count_adr_net_los(real_adr, real_adr_net_ota)
    real_adr_net_dc = count_adr_net_dc(real_adr_net_los)
    real_occ = count_occ(vals["occupancy"][0])
    real_occ_avg_val = Decimal((sum(real_occ) / len(real_occ)) * 100).quantize(
        Decimal("1."), rounding=ROUND_HALF_UP
    )
    real_occ_avg = real_occ_avg_val

    real_net_revenue = count_net_revenue(real_adr_net_dc, real_occ)
    real_net_revenue_sum_val = sum(real_net_revenue)
    real_net_revenue_sum = f"{real_net_revenue_sum_val:,}".replace(",", " ")
    real_net_revenue_formatted = [
        f"{revenue:,}".replace(",", " ") for revenue in real_net_revenue
    ]

    # 3. Оптимистичный сценарий
    optimistic_adr = count_adr(vals["adr"][1], vals["month"])
    optimistic_adr_net_ota = count_adr_net_ota(optimistic_adr)
    optimistic_adr_net_los = count_adr_net_los(optimistic_adr, optimistic_adr_net_ota)
    optimistic_adr_net_dc = count_adr_net_dc(optimistic_adr_net_los)
    optimistic_occ = count_occ(vals["occupancy"][1])
    optimistic_net_revenue = count_net_revenue(optimistic_adr_net_dc, optimistic_occ)
    optimistic_net_revenue_sum_val = sum(optimistic_net_revenue)
    optimistic_net_revenue_sum = f"{optimistic_net_revenue_sum_val:,}".replace(",", " ")

    max_val = max(max(real_net_revenue), max(optimistic_net_revenue))

    # 4. Генерация PDF (структура близка к HTML-шаблону)
    base_dir = Path(__file__).resolve().parent
    filename = safe_filename(f"Расчет доход по {address}") + ".pdf"
    output_path = base_dir / filename

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Heading1"],
        fontSize=20,
        leading=24,
        alignment=1,
        spaceAfter=16,
    )
    section_title = ParagraphStyle(
        "SectionTitle",
        parent=styles["Heading2"],
        fontSize=14,
        leading=18,
        spaceBefore=10,
        spaceAfter=4,
    )
    normal = styles["Normal"]

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )
    story = []

    story.append(Paragraph("Расчет ожидаемого дохода", title_style))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Адрес:", section_title))
    story.append(Paragraph(address, normal))
    story.append(Spacer(1, 4))

    story.append(Paragraph("Площадь (м²):", section_title))
    story.append(Paragraph(str(square), normal))
    story.append(Spacer(1, 4))

    story.append(Paragraph("Тип:", section_title))
    story.append(Paragraph(f"Квартира, {rooms}", normal))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Распределения выручки в рамках календарного года", section_title))

    months_names = [
        "январь", "февраль", "март", "апрель",
        "май", "июнь", "июль", "август",
        "сентябрь", "октябрь", "ноябрь", "декабрь",
    ]
    table_data = [["Месяц", "Доход (реальный), ₽"]]
    for m, v in zip(months_names, real_net_revenue_formatted):
        table_data.append([m.capitalize(), v])

    table = Table(table_data, colWidths=[5 * cm, 8 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f0f0")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 12))

    story.append(
        Paragraph(
            "Ожидаемый годовой доход (на руки, после вычета комиссии):",
            section_title,
        )
    )
    story.append(Paragraph(f"{real_net_revenue_sum} ₽", normal))
    story.append(Spacer(1, 6))

    story.append(Paragraph("Потенциал роста:", section_title))
    story.append(Paragraph(f"{optimistic_net_revenue_sum} ₽", normal))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Как формируется ожидаемый доход", section_title))
    story.append(
        Paragraph(
            f"Средняя стоимость ночи проживания для гостя (руб.): {real_avg_adr} ₽.",
            normal,
        )
    )
    story.append(
        Paragraph(
            f"Средняя загрузка по году* (% забронированных ночей): {real_occ_avg}%.",
            normal,
        )
    )
    story.append(Spacer(1, 8))

    story.append(
        Paragraph(
            "Ваш доход (за год) рассчитан за вычетом комиссии сторонних площадок за бронирования (15%) "
            "и за вычетом комиссии за управление объектом (10%, включая управление объектом "
            "и ценообразованием на площадках, обработку заказов, 24*7 обслуживание гостей).",
            normal,
        )
    )
    story.append(Spacer(1, 8))

    story.append(
        Paragraph(
            "Что мы дополнительно учитывали при оценке дохода по квартире:",
            section_title,
        )
    )
    story.append(
        Paragraph(
            "- Транспортная доступность (удаленность от метро и от центра города);<br/>"
            "- Наличие точек притяжения у района, где расположена квартира;<br/>"
            "- Параметры квартиры и дома;<br/>"
            "- Изменение спроса, связанное с сезонами, событиями в городе и пр.",
            normal,
        )
    )
    story.append(Spacer(1, 6))
    story.append(Paragraph("* - учитываются сезонные корректировки.", normal))

    doc.build(story)

    message = f"""Здравствуйте!

Меня зовут {manager_name}. Мы подготовили расчёт дохода по вашей квартире по адресу: {address}.

Предварительный годовой доход:
- {real_net_revenue_sum} ₽
- с потенциалом роста до {optimistic_net_revenue_sum} ₽

В файле приложены ожидаемые помесячные показатели. Пожалуйста, посмотрите их.
Если возникнут вопросы — можем созвониться или обсудить здесь, как вам будет удобнее.

Будем благодарны за вашу обратную связь."""
    return str(output_path), message
