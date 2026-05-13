from bs4 import BeautifulSoup
from typing import List, Dict
import requests


def parse_timetable_page(html: str) -> List[Dict]:
    """
    Парсит HTML-страницу расписания преподавателя с timetable.spbu.ru.
    Работает с русской и английской версией сайта.
    """
    soup = BeautifulSoup(html, 'html.parser')

    days_panels = soup.find_all('div', class_='panel panel-default')
    result = []

    for panel in days_panels:
        # День недели
        day_tag = panel.find('h4', class_='panel-title')
        if not day_tag:
            continue
        day = day_tag.text.strip()

        # Пары этого дня
        for item in panel.find_all('li', class_='common-list-item'):

            # --- Время ---
            time_div = item.find('div', class_='with-icon')
            time_tag = None
            if time_div:
                time_tag = time_div.find('span', title=lambda t: t and t in ['Время', 'Time'])
            time = time_tag.text.strip() if time_tag else ""

            # --- Предмет ---
            subject_tag = item.find('span', title=lambda t: t and t in ['Предмет', 'Subject'])
            subject = subject_tag.text.strip() if subject_tag else ""

            # --- Аудитория ---
            address_tag = item.find('span', class_='hoverable link')
            address = address_tag.text.strip() if address_tag else ""

            # --- Даты ---
            dates_container = item.find('div', class_='studyevent-datetime')
            if not dates_container:
                continue

            date_blocks = dates_container.find_all('div', class_='with-icon')

            dates = []
            for block in date_blocks:
                info_spans = block.find_all('span', class_='moreinfo')
                for span in info_spans:
                    title = span.get('title', '')
                    text = span.text.strip()
                    if title in ['Время', 'Time']:
                        continue
                    dates.append(text)

            for date in dates:
                result.append({
                    'day': day,
                    'date': date,
                    'time': time,
                    'subject': subject,
                    'address': address
                })

    return result


def format_schedule_text(parsed: List[Dict]) -> str:
    """Превращает распаршенное расписание в читаемый текст."""
    if not parsed:
        return "Расписание не найдено."

    lines = []
    current_day = ""

    for p in parsed:
        if p['day'] != current_day:
            current_day = p['day']
            lines.append(f"\n=== {current_day} ===")
        line = f"  {p['date']} | {p['time']} | {p['subject']}"
        if p['address']:
            line += f"\n    {p['address']}"
        lines.append(line)

    return '\n'.join(lines)

if __name__ == "__main__":

    url = "https://timetable.spbu.ru/EducatorEvents/1379"
    response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})

    parsed = parse_timetable_page(response.text)
    text_for_llm = format_schedule_text(parsed)
    print(text_for_llm)