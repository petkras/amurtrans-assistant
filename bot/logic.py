"""Детерминированная проверка заявки для учебного бота."""

from __future__ import annotations

import re

WIKI = "https://petkras.github.io/amurtrans-kontrol/"
DASHBOARD = "https://dashboard-tan-seven-92.vercel.app/"
FIELDS = (
    ("Отправитель", "sender"),
    ("Откуда", "origin"),
    ("Куда", "destination"),
    ("Груз", "cargo"),
    ("Мест", "places"),
    ("Масса, т", "weight"),
    ("Дата погрузки", "date"),
    ("Контакт", "contact"),
)
EMPTY = {"", "—", "-", "не знаю", "нет", "уточняется", "?"}
TEMPLATE = "\n".join(f"{label}: " for label, _ in FIELDS)


def parse_form(text: str) -> tuple[dict[str, str], list[str]]:
    values: dict[str, str] = {}
    unknown: list[str] = []
    aliases = {label.casefold(): key for label, key in FIELDS}
    for line in text.splitlines():
        if ":" not in line:
            if line.strip():
                unknown.append(line.strip())
            continue
        label, value = line.split(":", 1)
        key = aliases.get(label.strip().casefold())
        if key is None:
            if line.strip():
                unknown.append(line.strip())
            continue
        values[key] = value.strip()[:300]
    return values, unknown


def validate_form(values: dict[str, str]) -> list[str]:
    errors = []
    for label, key in FIELDS:
        if values.get(key, "").strip().casefold() in EMPTY:
            errors.append(f"• {label}")
    places = values.get("places", "").strip()
    if places and places.casefold() not in EMPTY and (not places.isdigit() or int(places) < 1):
        errors.append("• Мест — нужно целое число больше нуля")
    weight = values.get("weight", "").strip().replace(",", ".")
    if weight and weight.casefold() not in EMPTY:
        try:
            if float(weight) <= 0:
                raise ValueError
        except ValueError:
            errors.append("• Масса, т — нужно положительное число")
    date = values.get("date", "")
    if date and date.casefold() not in EMPTY and not re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", date):
        errors.append("• Дата погрузки — формат ДД.ММ.ГГГГ")
    return errors


def reply(text: str) -> str:
    command = text.strip().split(maxsplit=1)[0].split("@", 1)[0].lower() if text.strip() else ""
    if command == "/start":
        return ("Здравствуйте! Я помощник «АмурТранс Контроль». Помогу собрать сведения "
                "для заявки на перевозку и подскажу, что уточнить.\n\n"
                "Начните с /new. Документация проекта: " + WIKI)
    if command == "/help":
        return ("/new — шаблон заявки\n/example — пример заполнения\n/wiki — Wiki продукта\n"
                "/dashboard — демонстрационная аналитика\n"
                "/help — эта подсказка\n\nЗаполните шаблон одним сообщением. Для пустого поля оставьте строку после двоеточия пустой.")
    if command == "/wiki":
        return "Wiki «АмурТранс Контроль»: " + WIKI
    if command == "/dashboard":
        return ("Интерактивный дашборд обработки заказов: " + DASHBOARD
                + "\nПоказатели построены на демонстрационных данных. Можно загрузить свой CSV по указанной на странице схеме.")
    if command == "/new":
        return "Заполните поля и отправьте всё одним сообщением:\n\n" + TEMPLATE
    if command == "/example":
        return ("Демонстрационная заявка:\n\nОтправитель: ООО АмурЭлектро\n"
                "Откуда: Комсомольск-на-Амуре, ул. Примерная, 1\n"
                "Куда: Хабаровск, ул. Примерная, 2\nГруз: электрооборудование\n"
                "Мест: 4\nМасса, т: 3,2\nДата погрузки: 26.09.2026\n"
                "Контакт: +7 900 000-00-00\n\nЭто учебный пример. Пришлите свою заявку по /new.")
    if command.startswith("/"):
        return "Такой команды нет. Откройте /help."

    values, unknown = parse_form(text)
    if not values:
        return "Я проверяю заявки по шаблону. Введите /new и заполните поля."
    errors = validate_form(values)
    if errors:
        return ("Чтобы передать заявку менеджеру, уточните:\n" + "\n".join(errors)
                + "\n\nИсправьте шаблон и отправьте его целиком ещё раз. Заявка пока не подтверждена.")
    summary = "\n".join(f"{label}: {values[key]}" for label, key in FIELDS)
    note = "\n\nНеизвестные строки не учтены: " + "; ".join(unknown[:3]) if unknown else ""
    return ("Данные заявки заполнены:\n\n" + summary + note
            + "\n\nЭто черновик для проверки менеджером. Цена, исполнитель и принятие заказа здесь не подтверждаются.")
