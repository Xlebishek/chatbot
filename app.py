import transformers
transformers.logging.set_verbosity_error()

from agents import agents_dict, init_rag_components
from router import router_agent

import streamlit as st

from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

@st.cache_resource
def load_model():
    print("Загрузка модели")
    model = SentenceTransformer("data/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    print("Модель загружена")
    return model

@st.cache_resource
def load_qdrant():
    print("Подключение к Qdrant")
    path = "data/qdrant_storage"
    client = QdrantClient(path=path)
    print("Qdrant готов")
    return client

model = load_model()
qdrant_client = load_qdrant()

init_rag_components(model, qdrant_client)

st.set_page_config(page_title="Помощник", page_icon="🎓", layout="wide")

st.title("Университетский AI-ассистент")
st.write("Streamlit работает!")

# тыкалка для обновления
if "counter" not in st.session_state:
    st.session_state.counter = 0

if st.button("Нажми меня"):
    st.session_state.counter += 1

st.write(f"Счётчик нажатий: {st.session_state.counter}")

# состояние системы
if "now_agent" not in st.session_state:
    st.session_state.now_agent = "router_agent"
if "messages" not in st.session_state:
    st.session_state.messages = []


# боковая панель
with st.sidebar:
    st.header("Состояния")
    st.write("Текущий агент:", st.session_state.now_agent)

# окно взаимодействия
prompt = st.chat_input("Скажите что-нибудь...")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})

    # получаем направление от маршрутизатора
    if st.session_state.now_agent == "router_agent":
        st.session_state.now_agent = router_agent(prompt)

    current_agent = agents_dict.get(st.session_state.now_agent)

    if current_agent is None:
        answer = "Извините, я не отвечаю на подобного рода вопросы, может помочь чем-то ещё?"
        st.session_state.now_agent = "router_agent"
    else:
        answer = current_agent(prompt, 'student') # st.session_state.user_name

        if answer == "error":
            answer = "Извините, я не отвечаю на подобного рода вопросы, может помочь чем-то ещё?"
            st.session_state.now_agent = "router_agent"

    st.session_state.messages.append({"role": "assistant", "content": answer})

    st.write(f"Вы написали: {prompt}")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])


