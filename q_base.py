from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from sentence_transformers import SentenceTransformer

import json
import os

models = [
    "harrier-oss-v1-0.6b",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    "intfloat/multilingual-e5-small"
    ]
model_name = models[-2]

model = SentenceTransformer(f"data/models/{model_name}", local_files_only=True)
print("Загрзука модели завершена")

path = "data/qdrant_storage"
client = QdrantClient(path=path)
print("База данных готова к работе!")

new_name = model_name

collections = client.get_collections().collections
if new_name not in [i.name for i in collections]:
    client.create_collection(
        collection_name=new_name,
        vectors_config=VectorParams(size=model.get_embedding_dimension(), distance=Distance.COSINE),
    )
    print(f"Коллекция '{new_name}' создана")
else:
    print(f"Коллекция '{new_name}' уже есть")


def load_files(files, path_files):
    points = []
    idx = 0
    for file in files:
        with open(f'{path_files}/{file}', 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"Успешная загрузка, размер: {len(data)}")

        for item in data:
            idx += 1
            text = item['page_content']

            vector = model.encode(text).tolist()

            point = PointStruct(
                id=idx,
                vector=vector,
                payload={
                    "text": text,
                    "source": item['metadata']['source'],
                    "page_title": item['metadata']['page_title'],
                    "question": item['metadata']['question'],
                    "type": item['metadata']['type'],
                    "topic": item['metadata']['topic'],
                    "idx": item['metadata']['idx'],
                }
            )

            points.append(point)

            print(f'Обработка {idx + 1} файла')

    return points

def update_files(files):
    pass

path_files = 'data/json_docs/300_80_0.8'
files = os.listdir(path_files)
print(f"Полученные файлы: {files}")

client.upsert(
        collection_name=new_name,
        points=load_files(files, path_files)
    )

client.close()


