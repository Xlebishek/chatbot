from langchain_gigachat.chat_models import GigaChat
from langchain.tools import tool
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
import arxiv

import API

from parser import parse_timetable_page, format_schedule_text
import requests

_global_model = None
_global_vector_store = None

def init_rag_components(model, vector_store):
    global _global_model, _global_vector_store
    _global_model = model
    _global_vector_store = vector_store
    print("[RAG] Компоненты инициализированы")

'''from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings'''


llm_academic = GigaChat(
    credentials=API.api_key,
    verify_ssl_certs=False
)

'''@lru_cache(maxsize=1)
def load_db():
    embeddings = HuggingFaceEmbeddings(
        model_name='sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True},
        cache_folder='models/teach_model'
    )

    bd = Chroma(
        persist_directory="data/data/teach_chroma_bd_",
        embedding_function=embeddings
    )
    return bd

'''
@tool(description="Поиск статей для выбранной темы диплома")
def arxiv_search(query: str) -> str:
    print("Вызов arxiv_search")
    
    try:
        client = arxiv.Client()
        search = arxiv.Search(
            query=query,
            max_results=3,
            sort_by=arxiv.SortCriterion.Relevance
        )

        results = []
        for result in client.results(search):
            results.append({
                "title": result.title,
                "summary": result.summary,
                "published": result.published.date().isoformat(),
                "pdf_url": result.pdf_url
            })

        output = ""
        for i, a in enumerate(results, start=1):
            output += f"{i}. {a['title']} ({a['published']}, {a['pdf_url']})\n\n"
        print(f"Результат arxiv_search:{output}")
        return output
        
    except Exception as e:
        print(f"[ARXIV ERROR] {e}")
        return "Не удалось выполнить поиск статей. Сервис arXiv временно недоступен. Попробуйте позже."

@tool(description="Поиск преподавателя во времени")
def schedule(name: str):
    print(f"Вызов schedule с запросом {name}")
    kostyl = {'коровкин': 1379, 'кижаева': 18353}
    obr = {1379: 'Коровкин Максим Васильевич', 18535: 'Кижаева Наталья'}

    url = f"https://timetable.spbu.ru/EducatorEvents/{kostyl[name.lower()]}"
    response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    parsed = parse_timetable_page(response.text)
    text_for_llm = format_schedule_text(parsed)

    print(f"[schedule]:\n {text_for_llm}")

    return f"Полное имя: {obr[kostyl[name.lower()]]}\n" + text_for_llm

'''@tool(description="Поиск преподавателя для диплома по названию предмета")
def teacher_search(query: str):
    print("Вызов teacher_search")
    db = load_db()
    result = db.similarity_search(query, k=2)
    return result
'''

@tool(description="Поиск информации в документах СПбГУ")
def rag_search(query: str) -> str:
    print(f"[RAG] Поиск по запросу: {query}")

    global _global_model, _global_vector_store

    if _global_model is None or _global_vector_store is None:
        return "Система поиска не инициализирована. Пожалуйста, перезапустите приложение."

    query_vector = _global_model.encode(query).tolist()

    ans = _global_vector_store.query_points(
        collection_name='data',
        query=query_vector,
        limit=3
    )

    output = ""
    for i, q in enumerate(ans.points, 1):
        payload = q.payload
        output += f"[{i}] Источник: {payload['source']}\n"
        output += f"    Текст: {payload.get('text', '')[:500]}...\n\n"

    return output

tools_academic = [arxiv_search, schedule]
tools_rag = [rag_search]

system_promp_1 = """
    Ты - академический помощник. Твоя задача - помогать с академическими вопросами.
    
    Никогда не используй инструменты, если у тебя нет всей необходимой информации!
    
    Примеры правильного поведения:
    
    Пример 1 (нужно уточнение):
    Пользователь: "Найди научного руководителя"
    Ты: "Конечно, помогу найти научного руководителя. По какой теме диплома вы ищете руководителя?"
    
    Пример 2 (все данные есть):
    Пользователь: "Найди научного руководителя по машинному обучению"
    Ты: [используешь teacher_search с запросом "машинное обучение"]
    
    Пример 3 (неподходящий запрос):
    Пользователь: "Какая сегодня погода?"
    Ты: error
    
    Доступные инструменты:
    - teacher_search(query): поиск преподавателей по теме диплома (требуется тема)
    - arxiv_search(query): поиск научных статей (требуется тема поиска)
    
    Помни: если не хватает данных для инструмента - запроси их. 
    Ты можешь отвечать только на темы: помочь с темой для диплома,
    выбор научного руководителя, остальные вопросы тебя не касаются, 
    возвращай - error
    """

system_promt_0 = """
    Ты - академический помощник. Твоя задача - помогать с академическими вопросами.
    
    Никогда не используй инструменты, если у тебя нет всей необходимой информации!
    
    Примеры правильного поведения:
    
    Пример 1 (нужно уточнение):
    Пользователь: "Найди научные статьи"
    Ты: "Конечно, помогу найти, по какой теме статьи искать?"
    
    Пример 2 (неподходящий запрос):
    Пользователь: "Какая сегодня погода?"
    Ты: error
    
    Пример 3:
    Пользователь: "Где(когда/как) я могу найти Кижаеву на неделе":
    Ты: Вызываешь schedule(Кижаева), читаешь ответ и выдаёшь только те даты, которые тебя интересуют(т.е. на неделе)
    Например, ответ: === Saturday === (один из дней)
    14.02 | 17:10–18:45 | Computer Workshop, final test (re-sitting), не берём, т.к. эта неделя это 04.05 - 10.05
    Присылай даты только с 4 мая по 10 мая, другие нельзя
    
    Доступные инструменты:
    - arxiv_search(query): поиск научных статей (требуется тема поиска)
    - schedule(name): поиск препода во времени, чтобы найти его на неделе, например (требуется имя препода)
    
    Помни: если не хватает данных для инструмента - запроси их. 
    Ты можешь отвечать только на темы: помочь с темой для диплома,
    выбор научного руководителя, остальные вопросы тебя не касаются, 
    возвращай - error
    Сегодня вторник 06.05(дата для поиска на неделе)
    """

rag_promt = '''
Ты — ассистент по приёму в Санкт-Петербургский государственный университет (СПбГУ). 
Твоя задача — отвечать на вопросы абитуриентов и студентов на основе предоставленных документов.
Ты берёшь запрос пользователя и вызываешь базу, чтобы узнать ответ.

Правила работы:
1. Используй ТОЛЬКО информацию из найденных фрагментов документов.
2. Если ответа нет в документах — прямо скажи: «Информации по этому вопросу в предоставленных документах нет».
3. Не используй свои общие знания о поступлении в вузы, опирайся исключительно на правила СПбГУ.
4. При ответе всегда указывай, из какого документа и какого пункта взята информация.
5. Отвечай на русском языке, вежливо и чётко.

Инструменты:
rag_search(str) - возваращет чанки релевантые по запросу.

Ты можешь отвечать только на темы: документация университета, правила,
остальные вопросы тебя не касаются, 
возвращай - error, если тебя не касается.

'''

academic_agent = create_agent(
    model=llm_academic, 
    tools=tools_academic, 
    system_prompt=system_promt_0,
    checkpointer=InMemorySaver()
)

rag_agent = create_agent(
    model=llm_academic,
    tools=tools_rag,
    system_prompt=rag_promt,
    checkpointer=InMemorySaver()
)


def ask_academic_agent(query: str, user_name: str) -> str:
    print(f'[ACADEMIC] Вопрос {query}')
    
    try:
        response = academic_agent.invoke(
            {"messages": [("user", query)]},
            {"configurable": {"thread_id": user_name}}
        )["messages"][-1].content
        
        print(f'[ACADEMIC] Ответ: {response}')
        return response
        
    except Exception as e:
        print(f'[ACADEMIC ERROR] {e}')
        return "Произошла ошибка при обработке запроса. Попробуйте позже."


def ask_rag_agent(query: str, user_name: str) -> str:
    print(f'[RAG] Вопрос {query}')

    try:
        response = rag_agent.invoke(
            {"messages": [("user", query)]},
            {"configurable": {"thread_id": user_name}}
        )["messages"][-1].content

        print(f'[RAG] Ответ: {response}')
        return response

    except Exception as e:
        print(f'[RAG ERROR] {e}')
        return "Произошла ошибка при обработке запроса. Попробуйте позже."

agents_dict = {
    "academic_agent": ask_academic_agent,
    "rag_agent": ask_rag_agent
}