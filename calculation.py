import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import re
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

def safe_filename(name: str) -> str:
    name = re.sub(r'[<>:\"\/\\|?*\x00-\x1f]', '_', name)
    return name.strip().rstrip('.')

def count_adr(adr, month):
    k_adr = {1: 0.99, 2: 0.91, 3: 0.95, 4: 1, 5: 1.05, 6: 1.1,
             7: 1.09, 8: 1.07, 9: 1.07, 10: 1, 11: 0.92, 12: 1.1}
    res = []
    for k_adr_val in k_adr.values():
        res.append((adr / k_adr[month]) * k_adr_val)
    return res

def count_occ(occ):
    k_occ = {1: 0.7, 2: 0.8, 3: 0.8, 4: 0.9, 5: 1.05, 6: 1.15,
             7: 1.25, 8: 1.2, 9: 1.05, 10: 0.95, 11: 0.8, 12: 0.95}
    res = []
    for k_occ_val in k_occ.values():
        res.append(min(0.9, (occ / k_occ[1]) * k_occ_val))
    return res

def generate_pdf_and_message(address, rooms, square, adr_real):
    month = datetime.date.today().month
    avg_adr = sum(adr_real) / len(adr_real)
    
    vals = {
        'address': address,
        'rooms': rooms,
        'square': square,
        'adr': [avg_adr, avg_adr],
        'occupancy': [0.53, 0.583],
        'month': month
    }
    
    # Точные расчеты из вашего кода
    real_adr = count_adr(vals['adr'][0], month)
    real_avg_adr = f"{Decimal(sum(real_adr) / len(real_adr)).quantize(Decimal('1.'), rounding=ROUND_HALF_UP):,}".replace(",", " ")
    real_occ = count_occ(vals['occupancy'][0])
    real_occ_avg = f"{Decimal((sum(real_occ) / len(real_occ))*100).quantize(Decimal('1.'), rounding=ROUND_HALF_UP)}%"
    
    # 12 месяцев дохода (упрощенно для демонстрации)
    months = ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн', 
              'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек']
    real_net_revenue = [Decimal(85000 + i*5000) for i in range(12)]
    real_net_revenue_sum = f"{sum(real_net_revenue):,}".replace(",", " ")
    real_net_revenue_formatted = [f"{revenue:,}".replace(",", " ") for revenue in real_net_revenue]
    
    optimistic_net_revenue_sum = f"{sum(real_net_revenue)*1.07:,}".replace(",", " ")
    
    filename = safe_filename(f"Расчет доход по {address}") + ".pdf"
    
    # Создаем стили как в вашем HTML
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=1,  # center
        textColor=colors.darkblue
    )
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Heading2'],
        fontSize=16,
        spaceAfter=12,
        textColor=colors.darkgreen
    )
    
    doc = SimpleDocTemplate(filename, pagesize=A4, topMargin=2*cm)
    story = []
    
    # Заголовок
    story.append(Paragraph("📈 РАСЧЕТ ДОХОДНОСТИ ПОСУТОЧНОЙ СДАЧИ", title_style))
    story.append(Spacer(1, 20))
    
    # Информация об объекте
    story.append(Paragraph("📍 Информация об объекте", header_style))
    info_data = [
        ['Адрес', address],
        ['Формат', rooms],
        ['Площадь', f"{square} м²"],
        ['Средний чек (ADR)', real_avg_adr + ' ₽'],
        ['Заполняемость', real_occ_avg]
    ]
    info_table = Table(info_data, colWidths=[3.5*cm, 11*cm])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 30))
    
    # Результаты
    story.append(Paragraph("💰 РЕЗУЛЬТАТЫ РАСЧЕТА", header_style))
    story.append(Paragraph(f"<b>Базовый годовой доход: {real_net_revenue_sum} ₽</b>", styles['Heading2']))
    story.append(Paragraph(f"<b>Потенциал роста: {optimistic_net_revenue_sum} ₽</b>", styles['Heading2']))
    story.append(Spacer(1, 20))
    
    # Таблица помесячных показателей
    story.append(Paragraph("📊 Помесячная динамика", header_style))
    month_data = [['Месяц'] + months]
    month_data.append(['Доход, ₽'] + real_net_revenue_formatted)
    
    month_table = Table(month_data, colWidths=[2*cm, 1.5*cm]*6)
    month_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.lightgrey, colors.white]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(month_table)
    
    doc.build(story)
    
    # Сообщение остается тем же
    message = f"""Здравствуйте!

Меня зовут Ирина. Мы подготовили расчёт дохода по вашей квартире по адресу: {address}.

Предварительный годовой доход: 
- {real_net_revenue_sum} ₽
- с потенциалом роста до {optimistic_net_revenue_sum} ₽

В файле приложены ожидаемые помесячные показатели. Пожалуйста, посмотрите их.
Если возникнут вопросы — можем созвониться или обсудить здесь, как вам будет удобнее.

Будем благодарны за вашу обратную связь."""
    
    return filename, message
