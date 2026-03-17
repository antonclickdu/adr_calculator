import datetime
from decimal import Decimal, ROUND_HALF_UP
from jinja2 import Environment, FileSystemLoader
from pyhtml2pdf import converter
from pathlib import Path
import re
import os

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

def count_adr_net_ota(adr_list):
    adr_net_ota_percent = 0.15
    return [adr * (1 - adr_net_ota_percent) for adr in adr_list]

def count_adr_net_los(adr_list, adr_net_ota_list):
    return_rate = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0,
                   7: 0.05, 8: 0.05, 9: 0.05, 10: 0.05, 11: 0.05, 12: 0.05}
    res = []
    for month, (adr, adr_net_ota) in enumerate(zip(adr_list, adr_net_ota_list)):
        res.append(((1 - return_rate[month + 1]) * adr_net_ota) +
                   (return_rate[month + 1]) * adr)
    return res

def count_adr_net_dc(adr_net_los_list):
    adr_net_dc_percent = 0.10
    return [adr_net_los * (1 - adr_net_dc_percent) for adr_net_los in adr_net_los_list]

def count_occ(occ):
    k_occ = {1: 0.7, 2: 0.8, 3: 0.8, 4: 0.9, 5: 1.05, 6: 1.15,
             7: 1.25, 8: 1.2, 9: 1.05, 10: 0.95, 11: 0.8, 12: 0.95}
    res = []
    for k_occ_val in k_occ.values():
        res.append(min(0.9, (occ / k_occ[1]) * k_occ_val))
    return res

def count_net_revenue(adr_net_dc_list, occ_list):
    days_in_month = {1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30,
                     7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}
    res = []
    for month, (adr_net_dc, occ) in enumerate(zip(adr_net_dc_list, occ_list)):
        res.append(Decimal(days_in_month[month + 1] * adr_net_dc * occ)
                   .quantize(Decimal('1.'), rounding=ROUND_HALF_UP))
    return res

def generate_pdf_and_message(address, rooms, square, adr_real):
    month = datetime.date.today().month
    vals = {
        'address': address,
        'rooms': rooms,
        'square': square,
        'adr': [sum(adr_real)/len(adr_real), sum(adr_real)/len(adr_real)],
        'occupancy': [0.53, 0.53 * 1.1],  # Из вашего кода
        'month': month
    }
    
    # Real расчеты
    real_adr = count_adr(vals['adr'][0], month)
    real_avg_adr = f"{Decimal(sum(real_adr) / len(real_adr)).quantize(Decimal('1.'), rounding=ROUND_HALF_UP):,}".replace(",", " ")
    real_adr_net_ota = count_adr_net_ota(real_adr)
    real_adr_net_los = count_adr_net_los(real_adr, real_adr_net_ota)
    real_adr_net_dc = count_adr_net_dc(real_adr_net_los)
    real_occ = count_occ(vals['occupancy'][0])
    real_occ_avg = Decimal((sum(real_occ) / len(real_occ)) * 100).quantize(Decimal('1.'), rounding=ROUND_HALF_UP)
    real_net_revenue = count_net_revenue(real_adr_net_dc, real_occ)
    real_net_revenue_sum = f"{sum(real_net_revenue):,}".replace(",", " ")
    
    # Optimistic расчеты
    optimistic_adr = count_adr(vals['adr'][1], month)
    optimistic_adr_net_ota = count_adr_net_ota(optimistic_adr)
    optimistic_adr_net_los = count_adr_net_los(optimistic_adr, optimistic_adr_net_ota)
    optimistic_adr_net_dc = count_adr_net_dc(optimistic_adr_net_los)
    optimistic_occ = count_occ(vals['occupancy'][1])
    optimistic_net_revenue = count_net_revenue(optimistic_adr_net_dc, optimistic_occ)
    optimistic_net_revenue_sum = f"{sum(optimistic_net_revenue):,}".replace(",", " ")
    
    max_val = max(max(real_net_revenue), max(optimistic_net_revenue))
    real_net_revenue_formatted = [f"{revenue:,}".replace(",", " ") for revenue in real_net_revenue]
    
    res_to_templ = {
        'address': vals['address'],
        'rooms': vals['rooms'],
        'square': vals['square'],
        'real_avg_adr': real_avg_adr,
        'real_occ_avg': real_occ_avg,
        'real_net_revenue_sum': real_net_revenue_sum,
        'optimistic_net_revenue_sum': optimistic_net_revenue_sum,
        'max_val': max_val,
        'optimistic_net_revenue': optimistic_net_revenue,
        'real_net_revenue': real_net_revenue,
        'real_net_revenue_formatted': real_net_revenue_formatted,
    }
    
    # Генерация PDF
    env = Environment(loader=FileSystemLoader("."))
    templ = env.get_template("template.html")
    html_string = templ.render(res_to_templ)
    
    filename = safe_filename(f"Расчет доход по {vals['address']}") + ".pdf"
    converter.convert(html_string, filename)
    
    # Сообщение
    message = f"""Здравствуйте!

Меня зовут Ирина. Мы подготовили расчёт дохода по вашей квартире по адресу: {vals['address']}.

Предварительный годовой доход: 
- {real_net_revenue_sum} ₽
- с потенциалом роста до {optimistic_net_revenue_sum} ₽

В файле приложены ожидаемые помесячные показатели. Пожалуйста, посмотрите их.
Если возникнут вопросы — можем созвониться или обсудить здесь, как вам будет удобнее.

Будем благодарны за вашу обратную связь."""
    
    return filename, message
