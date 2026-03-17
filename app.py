import streamlit as st
from calculation import generate_pdf_and_message
from urllib.parse import quote

st.set_page_config(page_title="Калькулятор доходности", layout="wide")

st.title("🧮 Калькулятор доходности квартир")

# Шаг 1 или Шаг 2
step = st.session_state.get('step', 1)

if step == 1:
    st.header("Шаг 1: Параметры квартиры")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        address = st.text_input("Адрес", value="Москва, Улица Адмирала Корнилова, 76 к1")
    with col2:
        rooms = st.text_input("Комнаты", value="2 комната")
    with col3:
        square = st.text_input("Площадь", value="40,05")
    
    if st.button("Получить URL Sutochno.ru", type="primary"):
        address_term = quote(address.replace(" ", "+"))
        url = f"https://sutochno.ru/front/searchapp/search?guests_adults=2&occupied=2026-03-15;2026-03-17&term={address_term}"
        st.session_state.url = url
        st.session_state.address = address
        st.session_state.rooms = rooms
        st.session_state.square = square
        st.session_state.step = 2
        st.success(f"✅ URL готов!")
        st.code(url)
        st.rerun()

elif step == 2:
    st.header("Шаг 2: ADRs конкурентов")
    
    st.info(f"📍 URL из шага 1: {st.session_state.get('url', 'Не найден')}")
    
    adr_real = st.text_input(
        "ADRs (через запятую, руб)", 
        value="3600,5000,2596,5280,6500",
        help="Введите цены за ночь конкурентов, разделенные запятыми"
    )
    
    if st.button("🎯 Сгенерировать PDF и сообщение", type="primary"):
        try:
            adrs = [float(x.strip()) for x in adr_real.split(",")]
            pdf_path, message = generate_pdf_and_message(
                st.session_state.address,
                st.session_state.rooms,
                st.session_state.square,
                adrs
            )
            
            st.session_state.pdf_path = pdf_path
            st.session_state.message = message
            st.success("✅ PDF и сообщение созданы!")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Ошибка: {str(e)}")
    
    if 'pdf_path' in st.session_state:
        st.subheader("📄 Скачать PDF")
        with open(st.session_state.pdf_path, "rb") as f:
            st.download_button(
                label="⬇️ Скачать PDF",
                data=f.read(),
                file_name=f"Расчет_доход_{st.session_state.address[:30]}.pdf",
                mime="application/pdf"
            )
        
        st.subheader("💬 Готовое сообщение")
        st.text_area("📋 Скопируйте:", value=st.session_state.message, height=200, disabled=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Новый расчет"):
                for key in ['step', 'url', 'address', 'rooms', 'square', 'pdf_path', 'message']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
