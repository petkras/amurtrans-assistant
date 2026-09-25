import unittest

from bot.logic import parse_form, reply, validate_form


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
        self.assertIn("Контакт", answer)
        self.assertIn("целое число", answer)
        self.assertIn("положительное число", answer)

    def test_unknown_message(self):
        self.assertIn("/new", reply("Сколько стоит перевозка?"))


if __name__ == "__main__":
    unittest.main()
