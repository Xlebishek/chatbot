from langchain_gigachat.chat_models import GigaChat
import API


llm = GigaChat(
    credentials=API.api_key,
    verify_ssl_certs=False,
)


def router_agent(query: str) -> str:
    prompt = f"""
    Ты - маршрутизатор запросов. Твоя задача - выбрать ТОЛЬКО ОДНОГО агента из списка ниже.
    НЕ добавляй никаких пояснений, кавычек, точек или лишних слов.
    Верни ТОЧНО одно из двух слов: academic_agent или RAG_agent
    
    Правила выбора:
    - academic_agent: вопросы про диплом, научные статьи, преподавателей, расписание пар, учебу
    - RAG_agent: любые вопросы про документы, приказы, правила, процедуры, восстановление, отчисление, перевод, справки
    
    Вопрос: {query}
    
    Твой ответ (только одно слово, без кавычек и точек):
    """
    response = llm.invoke(prompt).content.strip().lower()
    # Очищаем от кавычек, точек, пробелов
    print(f"[ROUTER]: {response}")
    response = response.strip('"\'.,!? \n')
    return response


if __name__ == "__main__":

    print(llm.invoke('Когда был создан сбер?').content)