import json
from typing import List, Dict
from functools import lru_cache
from langchain_core.documents import Document
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma


def json_to_docs(teachers_data: Dict) -> List[Document]:
    docs = []

    for teacher_name, courses in teachers_data.items():
        # Создаем отдельный документ для каждого курса
        for course in courses:
            page_content = course

            metadata = {
                "teacher_name": teacher_name,
                "course": course,  # один конкретный курс
                "all_courses": courses  # все курсы преподавателя (опционально)
            }

            docs.append(Document(page_content=page_content, metadata=metadata))

    print(f"Создано {len(docs)} документов (преподавателей: {len(teachers_data)})")
    return docs

def create_db(docs):
    embeddings = HuggingFaceEmbeddings(
        model_name="intfloat/multilingual-e5-small",
        cache_folder="data/models",
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )

    db = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        persist_directory="chrome_storage"
    )
    db.persist()

    print(f"БД создана. Добавлено {len(docs)} преподавателей")
    return db


@lru_cache(maxsize=1)
def load_db():
    embeddings = HuggingFaceEmbeddings(
        model_name="intfloat/multilingual-e5-small",
        cache_folder="data/models",
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )

    db = Chroma(
        persist_directory="chrome_storage",
        embedding_function=embeddings
    )

    return db

def search(query: str):
    k = 3
    print('#' * 50)
    print(f"Запрос: {query}")

    db = load_db()
    results = db.similarity_search(query, k=k)

    text = ''

    if not results:
        print("Ничего не найдено")
        return []

    for i, doc in enumerate(results, 1):
        teacher_name = doc.metadata['teacher_name']
        course = doc.metadata['course']
        text += f"{i}. {teacher_name} - курс: {course}\n"

    print(text)

    return results

def main():
    path = "json_files/themes.json"
    with open(path, 'r', encoding='utf-8') as file:
        data = json.load(file)

    docs = json_to_docs(data)

    print(docs)

    create_db(docs)



if __name__ == "__main__":

    #main()

    test = ["искуственный интеллект", "математика", "дифференциальные уравнения"]

    for i in test:
        search(i)