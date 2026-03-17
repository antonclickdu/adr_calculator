import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import re
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

def safe_filename(name: str) -> str:
    name = re.sub(r'[<>:\"\/\\|?*\x00-\x1f]', '_', name)
    return name.strip().rstrip('.')

def generate_pdf_and_message(address, rooms, square, adr_real):
    month = datetime.date.today().month
    
    # Расчеты (ваш оригинальный код)
    avg_adr = sum(adr_real) / len(adr_real)
    real_adr = [avg_adr * 0.95] * 12  # Упрощено для PDF
    optimistic_adr = [avg_adr * 1.05] * 12
    
    real_net_revenue_sum = f"{int(sum(real_adr) * 300):,}".replace(",", " ") + " ₽"
    optimistic_net_revenue_sum = f"{int(sum(optimistic_adr) * 330):,}".replace(",", " ") + " ₽"
    
    # PDF с ReportLab
    filename = safe_filename(f"Расчет доход по {address}") + ".pdf"
    
    doc = SimpleDocTemplate(filename, pagesize=A4)
    story = []
    styles = getSampleStyleSheet()
    
    # Заголовок
    story.append(Paragraph("📊 Расчет доходности квартиры", styles['Title']))
    story.append(Spacer(1, 20))
    
    # Основная информация
    data = [
        ["Адрес", address],
        ["Комнаты", rooms],
        ["Площадь", f"{square} м²"],
        ["Средний ADR", f"{avg_adr:,.0f} ₽"],
    ]
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(table)
    story.append(Spacer(1, 20))
    
    # Доходность
    story.append(Paragraph("💰 Предварительный годовой доход:", styles['Heading2']))
    story.append(Paragraph(f"• Базовый: <b>{real_net_revenue_sum}</b>", styles['Normal']))
    story.append(Paragraph(f"• Потенциал роста: <b>{optimistic_net_revenue_sum}</b>", styles['Normal']))
    
    doc.build(story)
    
    # Сообщение
    message = f"""Здравствуйте!

Меня зовут Ирина. Мы подготовили расчёт дохода по вашей квартире по адресу: {address}.

Предварительный годовой доход: 
- {real_net_revenue_sum}
- с потенциалом роста до {optimistic_net_revenue_sum}

В приложенном файле подробный расчет. Пожалуйста, посмотрите.
Если возникнут вопросы — можем созвониться или обсудить здесь.

Будем благодарны за обратную связь!"""
    
    return filename, message
