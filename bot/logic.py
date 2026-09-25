"""Диалоговый сбор заявки для учебного Telegram-бота."""

from __future__ import annotations

import re
import time

WIKI = "https://petkras.github.io/amurtrans-kontrol/"
DASHBOARD = "https://dashboard-tan-seven-92.vercel.app/"
FIELDS = (
    ("Отправитель", "sender", "Кто отправитель? Напишите название компании или ФИО."),
    ("Откуда", "origin", "Откуда забрать груз? Укажите город и адрес."),
    ("Куда", "destination", "Куда доставить груз? Укажите город и адрес."),
    ("Груз", "cargo", "Какой груз нужно перевезти?"),
    ("Мест", "places", "Сколько грузовых мест? Укажите целое число."),
    ("Масса, т", "weight", "Какова масса груза в тоннах? Можно указать дробное число, например 3,2."),
    ("Дата погрузки", "date", "На какую дату нужна погрузка? Формат: ДД.ММ.ГГГГ."),
    ("Контакт", "contact", "Как связаться с отправителем? Укажите телефон или Telegram."),
)
EMPTY = {"", "—", "-", "не знаю", "нет", "уточняется", "?"}
SESSIONS: dict[int, dict] = {}
SESSION_TTL_SECONDS = 30 * 60


def parse_form(text: str) -> tuple[dict[str, str], list[str]]:
    values: dict[str, str] = {}
    unknown: list[str] = []
    aliases = {label.casefold(): key for label, key, _ in FIELDS}
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


def validate_value(key: str, value: str) -> str | None:
    normalized = value.strip()
    if normalized.casefold() in EMPTY:
        return "Это обязательное поле."
    if key == "places" and (not normalized.isdigit() or int(normalized) < 1):
        return "Нужно целое число больше нуля."
    if key == "weight":
        try:
            if float(normalized.replace(",", ".")) <= 0:
                raise ValueError
        except ValueError:
            return "Введите положительное число, например 3,2."
    if key == "date" and not re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", normalized):
        return "Используйте формат ДД.ММ.ГГГГ, например 26.09.2026."
    return None


def validate_form(values: dict[str, str]) -> list[str]:
    errors = []
    for label, key, _ in FIELDS:
        problem = validate_value(key, values.get(key, ""))
        if problem:
            if key == "places":
                errors.append("• Мест — нужно целое число больше нуля")
            elif key == "weight":
                errors.append("• Масса, т — нужно положительное число")
            elif key == "date":
                errors.append("• Дата погрузки — формат ДД.ММ.ГГГГ")
            else:
                errors.append(f"• {label}")
    return errors


def _command(text: str) -> str:
    return text.strip().split(maxsplit=1)[0].split("@", 1)[0].lower() if text.strip() else ""


def reply(text: str) -> str:
    """Ответы на команды и проверка присланной целиком старой формы."""
    command = _command(text)
    if command == "/start":
        return ("Здравствуйте! Я помощник «АмурТранс Контроль». Помогу собрать сведения "
                "для заявки на перевозку и подскажу, что уточнить.\n\n"
                "Напишите /help, чтобы посмотреть команды, или /new, чтобы начать заявку.\n"
                "Документация проекта: " + WIKI)
    if command == "/help":
        return ("/new — начать заявку по шагам\n/example — пример заполнения\n/wiki — Wiki продукта\n"
                "/dashboard — демонстрационная аналитика\n/cancel — отменить текущую заявку\n"
                "/help — эта подсказка\n\nЯ запрашиваю поля по очереди, повторно отправлять всю заявку не нужно.")
    if command == "/wiki":
        return "Wiki «АмурТранс Контроль»: " + WIKI
    if command == "/dashboard":
        return ("Интерактивный дашборд обработки заказов: " + DASHBOARD
                + "\nПоказатели построены на демонстрационных данных.")
    if command == "/confirm":
        return "Сейчас нет черновика на подтверждение. Чтобы начать, напишите /new."
    if command == "/example":
        return ("Пример заявки:\nОтправитель: ООО АмурЭлектро\nОткуда: Комсомольск-на-Амуре\n"
                "Куда: Хабаровск\nГруз: электрооборудование\nМест: 4\nМасса, т: 3,2\n"
                "Дата погрузки: 26.09.2026\nКонтакт: +7 900 000-00-00\n\nЧтобы начать диалог, напишите /new.")
    if command.startswith("/"):
        return "Такой команды нет. Напишите /help, чтобы посмотреть список команд."
    values, _ = parse_form(text)
    if values:
        errors = validate_form(values)
        if errors:
            return "В форме нужно уточнить:\n" + "\n".join(errors) + "\n\nНапишите /new, и я спрошу только недостающие данные."
        summary = "\n".join(f"{label}: {values[key]}" for label, key, _ in FIELDS)
        return "Данные заявки заполнены:\n\n" + summary + "\n\nЭто черновик для проверки менеджером."
    return "Чтобы начать оформление, напишите /new. Список команд — /help."


def handle_message(chat_id: int, text: str) -> str:
    """Обрабатывает пошаговый диалог; состояние хранится только в памяти экземпляра."""
    command = _command(text)
    now = time.time()
    for key, session in list(SESSIONS.items()):
        if now - session["updated_at"] > SESSION_TTL_SECONDS:
            SESSIONS.pop(key, None)
    session = SESSIONS.get(chat_id)

    if command == "/new":
        SESSIONS[chat_id] = {"values": {}, "awaiting": FIELDS[0][1], "updated_at": now}
        return FIELDS[0][2]
    if command == "/cancel":
        SESSIONS.pop(chat_id, None)
        return "Текущая заявка отменена. Чтобы начать заново, напишите /new."
    if command == "/confirm":
        if not session or session.get("stage") != "confirm":
            return "Сейчас нет черновика на подтверждение. Чтобы начать, напишите /new."
        SESSIONS.pop(chat_id, None)
        return "Черновик подтверждён и подготовлен для проверки менеджером. Данные не отправлены в рабочую систему."
    if command.startswith("/"):
        return reply(text)

    if session and session.get("stage") == "confirm":
        return "Проверьте сводку и напишите /confirm для подтверждения черновика или /new, чтобы начать заново."
    if not session:
        submitted, _ = parse_form(text)
        if submitted:
            accepted = {
                key: value for key, value in submitted.items()
                if value.strip() and validate_value(key, value) is None
            }
            missing = next((item for item in FIELDS if item[1] not in accepted), None)
            if missing:
                SESSIONS[chat_id] = {
                    "values": accepted,
                    "awaiting": missing[1],
                    "updated_at": now,
                }
                return f"Получил заявку: заполнено {len(accepted)} из {len(FIELDS)} полей. Уточню только недостающее.\n\n{missing[2]}"
            return reply(text)
        return reply(text)
    key = session["awaiting"]
    field = next(item for item in FIELDS if item[1] == key)
    value = text.strip()[:300]
    problem = validate_value(key, value)
    if problem:
        session["updated_at"] = now
        return problem + "\n\n" + field[2]

    session["values"][key] = value
    session["updated_at"] = now
    next_field = next((item for item in FIELDS if item[1] not in session["values"]), None)
    if next_field:
        session["awaiting"] = next_field[1]
        return next_field[2]

    session["stage"] = "confirm"
    return ("Готово, все обязательные данные собраны. Проверьте черновик:\n\n"
            + _summary(session["values"])
            + "\n\nЕсли всё верно, напишите /confirm. Чтобы начать заново — /new.")


def _summary(values: dict[str, str]) -> str:
    return "\n".join(f"{label}: {values[field_key]}" for label, field_key, _ in FIELDS)
