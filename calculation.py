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


def generate_pdf_and_message(address: str, rooms: str, square: str, adr_real: list[float], manager_name: str):
    """
    Генерирует PDF с расчётом доходности с помощью ReportLab,
    без wkhtmltopdf/xhtml2pdf, максимально повторяя структуру template.html.
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

    # 3. Доход по месяцам (простая модель; можно заменить своей)
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

    # 4. Подготовка PDF
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

    # Заголовок — "Расчет ожидаемого дохода"
    story.append(Paragraph("Расчет ожидаемого дохода", title_style))
    story.append(Spacer(1, 8))

    # Блок: адрес, площадь, тип
    story.append(Paragraph("Адрес:", section_title))
    story.append(Paragraph(address, normal))
    story.append(Spacer(1, 4))

    story.append(Paragraph("Площадь (м²):", section_title))
    story.append(Paragraph(str(square), normal))
    story.append(Spacer(1, 4))

    story.append(Paragraph("Тип:", section_title))
    story.append(Paragraph(f"Квартира, {rooms}", normal))
    story.append(Spacer(1, 12))

    # Распределение выручки по месяцам (как в шаблоне)
    story.append(Paragraph("Распределения выручки в рамках календарного года", section_title))

    months = [
        "январь", "февраль", "март", "апрель",
        "май", "июнь", "июль", "август",
        "сентябрь", "октябрь", "ноябрь", "декабрь",
    ]

    table_data = [["Месяц", "Доход, ₽"]]
    for m, v in zip(months, real_net_revenue_formatted):
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

    # Ожидаемый доход + потенциал
    story.append(
        Paragraph(
            "Ожидаемый годовой доход:<br/>(на руки, после вычета комиссии)",
            section_title,
        )
    )
    story.append(Paragraph(f"{real_net_revenue_sum} ₽", normal))
    story.append(Spacer(1, 6))

    story.append(Paragraph("Потенциал роста:", section_title))
    story.append(Paragraph(f"{optimistic_net_revenue_sum} ₽", normal))
    story.append(Spacer(1, 12))

    # Важно! – текст как в template.html
    story.append(Paragraph("Важно!", section_title))
    story.append(
        Paragraph(
            "Указанный ожидаемый доход рассчитан на основе оптимальной рыночной "
            "стоимости ночи и прогнозируемой загрузки с учетом сезонности, конкуренции и пр. "
            "Фактический доход формируется из реальных бронирований. "
            "Все бронирования и начисления полностью прозрачны и доступны вам в личном кабинете. "
            "Мы учитываем ваши пожелания по ценообразованию. По вашему запросу мы можем пересмотреть "
            "стоимость ночей (в т.ч. повысить ее). "
            "Предоставленные расчеты несут ознакомительный характер, не является офертой.",
            normal,
        )
    )
    story.append(Spacer(1, 12))

    # Как формируется ожидаемый доход
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
    story.append(Spacer(1, 12))

    # Что учитывали
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

    # Сборка PDF
    doc.build(story)

    # Сообщение
    message = f"""Здравствуйте!

Меня зовут {manager_name}. Мы подготовили расчёт дохода по вашей квартире по адресу: {address}.

Предварительный годовой доход:
- {real_net_revenue_sum} ₽
- с потенциалом роста до {optimistic_net_revenue_sum} ₽

В файле приложены ожидаемые помесячные показатели. Пожалуйста, посмотрите их.
Если возникнут вопросы — можем созвониться или обсудить здесь, как вам будет удобнее.

Будем благодарны за вашу обратную связь."""
    return str(output_path), message
