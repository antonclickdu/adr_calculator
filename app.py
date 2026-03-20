import streamlit as st
from calculation import generate_pdf_and_message
from urllib.parse import quote

st.set_page_config(page_title="Калькулятор доходности", layout="wide")

st.title("🧮 Калькулятор доходности квартир")

step = st.session_state.get("step", 1)

if step == 1:
    st.header("Шаг 1: Параметры квартиры")

    col1, col2, col3 = st.columns(3)
    with col1:
        address = st.text_input(
            "Адрес",
            value="Москва, Улица Адмирала Корнилова, 76 к1",
        )
    with col2:
        rooms = st.text_input("Комнаты", value="2 комната")
    with col3:
        square = st.text_input("Площадь", value="40,05")

    # Новое поле — имя менеджера
    manager_name = st.text_input("Имя менеджера", value="Ирина")

    if st.button("Получить URL Sutochno.ru", type="primary"):
        address_term = quote(address.replace(" ", "+"))
        url = (
            "https://sutochno.ru/front/searchapp/search"
            f"?guests_adults=2&occupied=2026-03-15;2026-03-17&term={address_term}"
        )

        st.session_state.url = url
        st.session_state.address = address
        st.session_state.rooms = rooms
        st.session_state.square = square
        st.session_state.manager_name = manager_name
        st.session_state.step = 2

        st.success("✅ URL готов!")
        st.code(url)
        st.rerun()

elif step == 2:
    st.header("Шаг 2: ADRs конкурентов")

    st.info(f"📍 URL из шага 1: {st.session_state.get('url', 'Не найден')}")

    adr_real = st.text_input(
        "ADRs (через запятую, руб)",
        value="3600,5000,2596,5280,6500",
        help="Введите цены за ночь конкурентов, разделенные запятыми",
    )

    if st.button("🎯 Сгенерировать PDF и сообщение", type="primary"):
        try:
            adrs = [
                float(x.strip().replace(" ", ""))
                for x in adr_real.split(",")
                if x.strip()
            ]
            if not adrs:
                st.error("❌ Введите хотя бы одно значение ADR.")
            else:
                pdf_path, message = generate_pdf_and_message(
                    st.session_state.address,
                    st.session_state.rooms,
                    st.session_state.square,
                    adrs,
                    st.session_state.get("manager_name", "Ирина"),
                )
                st.session_state.pdf_path = pdf_path
                st.session_state.message = message
                st.success("✅ PDF и сообщение созданы!")
                st.rerun()
        except Exception as e:
            st.error(f"❌ Ошибка: {str(e)}")
