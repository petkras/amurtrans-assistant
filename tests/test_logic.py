import unittest
from copy import deepcopy

from bot.logic import SESSIONS, handle_message, parse_form, reply, validate_form


class LogicTests(unittest.TestCase):
    def test_complete_request(self):
        form = ("Отправитель: ООО АмурЭлектро\nОткуда: Комсомольск-на-Амуре\n"
                "Куда: Хабаровск\nГруз: оборудование\nМест: 4\nМасса, т: 3,2\n"
                "Дата погрузки: 26.09.2026\nКонтакт: +7 900 000-00-00")
        self.assertEqual(validate_form(parse_form(form)[0]), [])
        self.assertIn("Данные заявки заполнены", reply(form))

    def test_missing_and_invalid(self):
        form = "Откуда: Комсомольск-на-Амуре\nМест: ноль\nМасса, т: -1"
        answer = reply(form)
        self.assertIn("Масса, т", answer)
        self.assertIn("Дата погрузки", answer)

    def test_unknown_message(self):
        self.assertIn("/new", reply("Сколько стоит перевозка?"))

    def test_dashboard_command(self):
        self.assertIn("https://dashboard-tan-seven-92.vercel.app/", reply("/dashboard"))

    def test_start_mentions_help(self):
        self.assertIn("/help", reply("/start"))

    def test_help_lists_confirmation(self):
        self.assertIn("/confirm", reply("/help"))

    def test_dialog_collects_fields_without_resending_form(self):
        chat_id = 123456
        SESSIONS.pop(chat_id, None)
        self.assertIn("Кто отправитель", handle_message(chat_id, "/new"))
        prompts = ["ООО Тест", "Комсомольск", "Хабаровск", "Оборудование", "4", "3,2", "26.09.2026"]
        for answer in prompts:
            next_prompt = handle_message(chat_id, answer)
            self.assertNotIn("повторно", next_prompt.lower())
        result = handle_message(chat_id, "+7 900 000-00-00")
        self.assertIn("все обязательные данные собраны", result)
        self.assertIn("ООО Тест", result)
        self.assertIn(chat_id, SESSIONS)
        self.assertIn("Черновик подтверждён", handle_message(chat_id, "/confirm"))
        self.assertNotIn(chat_id, SESSIONS)

    def test_dialog_repeats_only_invalid_field(self):
        chat_id = 654321
        SESSIONS.pop(chat_id, None)
        handle_message(chat_id, "/new")
        handle_message(chat_id, "ООО Тест")
        handle_message(chat_id, "Комсомольск")
        handle_message(chat_id, "Хабаровск")
        handle_message(chat_id, "Груз")
        response = handle_message(chat_id, "ноль")
        self.assertIn("целое число", response)
        self.assertIn("Сколько грузовых мест", response)
        self.assertEqual(SESSIONS[chat_id]["values"]["sender"], "ООО Тест")

    def test_partial_form_prompts_only_missing_field(self):
        chat_id = 987654
        SESSIONS.pop(chat_id, None)
        partial = ("Отправитель: ООО Тест\nОткуда: Комсомольск\nКуда: Хабаровск\n"
                   "Груз: оборудование\nМест: 4\nМасса, т: 3,2\nДата погрузки: 26.09.2026")
        response = handle_message(chat_id, partial)
        self.assertIn("заполнено 7 из 8", response)
        self.assertIn("Как связаться", response)
        result = handle_message(chat_id, "+7 900 000-00-00")
        self.assertIn("все обязательные данные собраны", result)
        self.assertIn("Отправитель: ООО Тест", result)

    def test_dialog_writes_back_copied_sessions_after_each_answer(self):
        class CopyingStore(dict):
            def get(self, key, default=None):
                value = super().get(key, default)
                return deepcopy(value) if value is not default else default

        chat_id = 246810
        store = CopyingStore()
        handle_message(chat_id, "/new", sessions=store)
        handle_message(chat_id, "ООО Redis Тест", sessions=store)
        self.assertEqual(store[chat_id]["awaiting"], "origin")
        self.assertEqual(store[chat_id]["values"]["sender"], "ООО Redis Тест")

        invalid = handle_message(chat_id, "", sessions=store)
        self.assertIn("обязательное поле", invalid)
        self.assertEqual(store[chat_id]["awaiting"], "origin")
        handle_message(chat_id, "Комсомольск-на-Амуре, тестовый адрес", sessions=store)
        self.assertEqual(store[chat_id]["awaiting"], "destination")
        self.assertEqual(store[chat_id]["values"]["origin"], "Комсомольск-на-Амуре, тестовый адрес")


if __name__ == "__main__":
    unittest.main()
