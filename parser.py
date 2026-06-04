from bs4 import BeautifulSoup
from typing import Dict, List
from datetime import datetime, timedelta
import requests
import json


def get_schedule(url: str) -> Dict[str, Dict[str, List[Dict]]]:
    """
    Загружает расписание по ссылке и возвращает словарь:
    { "Day": { "DD.MM": [ {"time": "...", "subject": "...", "address": "..."} ] } }
    """
    response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')
    schedule = {}

    for panel in soup.find_all('div', class_='panel panel-default'):
        day_tag = panel.find('h4', class_='panel-title')
        if not day_tag:
            continue
        day_name = day_tag.get_text(strip=True)
        schedule[day_name] = {}

        for item in panel.find_all('li', class_='common-list-item'):
            # Время — ищем через иконку часов
            time = ""
            time_icon = item.find('i', class_='glyphicon-time')
            if time_icon:
                parent = time_icon.find_parent('div', class_='with-icon')
                if parent:
                    span = parent.find('span', class_='moreinfo')
                    if span:
                        time = span.get_text(strip=True)

            # Предмет — через иконку книги
            subject = ""
            subj_icon = item.find('i', class_='glyphicon-education')
            if subj_icon:
                parent = subj_icon.find_parent('div', class_='with-icon')
                if parent:
                    span = parent.find('span', class_='moreinfo')
                    if span:
                        subject = span.get_text(strip=True)

            # Адрес — через иконку маркера
            address = ""
            addr_icon = item.find('i', class_='glyphicon-map-marker')
            if addr_icon:
                addr_span = addr_icon.find_parent('div').find('span', class_='hoverable link')
                if addr_span:
                    address = addr_span.get_text(strip=True)

            # Собираем даты (исключаем блок со временем)
            dates_block = item.find('div', class_='studyevent-datetime')
            if not dates_block:
                continue

            date_strings = []
            for span in dates_block.find_all('span', class_='moreinfo'):
                title = span.get('title', '')
                if 'Время' not in title and 'Time' not in title:
                    txt = span.get_text(strip=True)
                    if txt:
                        date_strings.append(txt)

            if not date_strings:
                continue

            event = {"time": time, "subject": subject, "address": address}
            dedup_key = (time, subject, address)  # ключ для удаления дублей

            for date_str in date_strings:
                if date_str not in schedule[day_name]:
                    schedule[day_name][date_str] = []
                    schedule[day_name][date_str + "_seen"] = set()  # временное хранилище

                seen_set = schedule[day_name].get(date_str + "_seen", set())
                if dedup_key not in seen_set:
                    schedule[day_name][date_str].append(event.copy())
                    seen_set.add(dedup_key)

    # Удаляем служебные ключи "_seen"
    for day in schedule:
        keys_to_remove = [k for k in schedule[day] if k.endswith("_seen")]
        for k in keys_to_remove:
            del schedule[day][k]

    return schedule


def get_week_schedule(schedule_dict, monday_date_str):
    """
    Получает расписание на неделю, начиная с указанного понедельника.

    Args:
        schedule_dict: словарь с расписанием вида {day: {date_str: [lessons]}}
        monday_date_str: строка с датой понедельника в формате "DD.MM"

    Returns:
        dict: {date_str: {day_name: [lessons]}}
    """

    current_year = datetime.now().year
    monday_date = datetime.strptime(f"{current_year}.{monday_date_str}", "%Y.%d.%m")


    week_dates = {}
    days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    for i, day_name in enumerate(days_of_week):
        current_date = monday_date + timedelta(days=i)
        date_str = current_date.strftime("%d.%m")
        week_dates[date_str] = day_name


    def is_date_in_range(date_str, range_str):
        try:
            if "–" in range_str:
                # Диапазон вида "16.03–18.05 (10)"
                range_part = range_str.split(" (")[0]  # Отрезаем количество недель
                start_str, end_str = range_part.split("–")

                # Парсим даты диапазона
                start_date = datetime.strptime(f"{current_year}.{start_str}", "%Y.%d.%m")
                end_date = datetime.strptime(f"{current_year}.{end_str}", "%Y.%d.%m")
                target_date = datetime.strptime(f"{current_year}.{date_str}", "%Y.%d.%m")

                return start_date <= target_date <= end_date
            else:
                # Точная дата
                return date_str == range_str
        except:
            return date_str == range_str
        
    result = {}

    for day_name, dates_dict in schedule_dict.items():
        for date_key, lessons in dates_dict.items():
            # Попадает ли дата в неделю
            for week_date_str, week_day_name in week_dates.items():
                if is_date_in_range(week_date_str, date_key) and day_name == week_day_name:
                    if week_date_str not in result:
                        result[week_date_str] = {}
                    if day_name not in result[week_date_str]:
                        result[week_date_str][day_name] = []
                    result[week_date_str][day_name].extend(lessons)
                    break

    return result

if __name__ == "__main__":
    id = '18353'
    url = f"https://timetable.spbu.ru/EducatorEvents/{id}"

    with open("data/json_files/schedule.json", "r", encoding="utf-8") as file:
        save_schedule = json.load(file)

    if id not in save_schedule:
        print("Вызов")
        schedule = get_schedule(url)
        save_schedule[id] = schedule

    with open("data/json_files/schedule.json", "w", encoding="utf-8") as file:
        json.dump(save_schedule, file, ensure_ascii=False, indent=4)

    print(save_schedule[id])
    lessons = get_week_schedule(save_schedule[id], "16.02")

    for i, v in lessons.items():
        para = list(v.values())[0]



