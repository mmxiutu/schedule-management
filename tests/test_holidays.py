from datetime import date

from schedule_assistant.domain.holidays import KIND_HOLIDAY, day_kind, holiday_label_zh


def test_english_names_map_to_chinese():
    assert holiday_label_zh("National Day") == "国庆节"
    assert holiday_label_zh("Spring Festival") == "春节"
    assert holiday_label_zh("国庆节") == "国庆节"


def test_october_first_is_chinese_national_day():
    kind, label = day_kind(date(2026, 10, 1))
    assert kind == KIND_HOLIDAY
    assert label == "国庆节"
