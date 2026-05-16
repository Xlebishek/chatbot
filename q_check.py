from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from qdrant_client.models import Filter, FieldCondition, MatchValue

model = SentenceTransformer("data/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
print("Загрзука модели завершена")

path = "data/qdrant_storage"
client = QdrantClient(path=path)
print("База данных готова к работе!")

name = 'data'

collection_info = client.get_collection(collection_name=name)
print(f"В коллекции {collection_info.points_count} записей")


query = "сколько баллов даёт олимпиада я профессионал"
query_vector = model.encode(query).tolist()

hits = client.query_points(
    collection_name=name,
    query=query_vector,
    limit=10
)

'''query_filter=Filter(
            must=[
                FieldCondition(
                    key='topic',
                    match=MatchValue(value='dormitory')
                )
            ]
        ),'''

for point in hits.points:
    print(point.payload['idx'])
    print(f"Score: {point.score}, {point.payload['source']}, Text: {point.payload['text']}")


'''query_filter=Filter(
            must=[
                FieldCondition(
                    key='topic',
                    match=MatchValue(value='dormitory')
                )
            ]
        ),'''

