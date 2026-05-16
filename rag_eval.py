from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from typing import List, Dict
import json

class Metrics:
    def __init__(self, name_model: str, path: str = "data/qdrant_storage"):
        self.path = path
        self.collection_name = name_model
        self.client = QdrantClient(path=path)
        print("База данных загружена")
        self.model = SentenceTransformer(name_model, local_files_only=True)
        print("Загрзука модели завершена")

    def hits_k(self, data: List[Dict], k_values: List[int] = [1, 3, 5, 10]):

        # Hits@k = (количество запросов, где релевантный документ попал в top-k) / (всего запросов)
        hits = {k: 0 for k in k_values}
        for query in data:
            print(f"Обработка вопроса: {query['query']}")
            vector = self.model.encode(query['query']).tolist()
            results = self.client.query_points(
                collection_name=self.collection_name,
                query=vector,
                limit=max(k_values)
            )

            result_idx = [point.payload['idx'] for point in results.points]

            for k in k_values:
                if any(idx in result_idx[:k] for idx in query['idx']):
                    hits[k] += 1


        return {k: hits[k] / len(data) for k in k_values}

    def mrr_at_10(self, data: List[Dict]) -> float:
        """
        MRR@10 (Mean Reciprocal Rank at 10) - среднее обратных рангов первого релевантного документа.

        Формула:
            MRR@10 = (1/|Q|) * Σ (1 / rank_i)

        где:
            |Q| - количество запросов
            rank_i - позиция первого релевантного документа для i-го запроса (1-indexed)
            если релевантный документ не найден в топ-10, то 1/rank_i = 0

        Returns:
            float: значение MRR@10 в диапазоне [0, 1]
        """
        total = len(data)
        sum_reciprocal_ranks = 0

        for query in data:
            print(f"Обработка вопроса: {query['query']}")
            vector = self.model.encode(query['query']).tolist()

            results = self.client.query_points(
                collection_name=self.collection_name,
                query=vector,
                limit=10
            )

            # Собираем idx найденных документов
            retrieved_idx = [point.payload.get('idx', str(point.id)) for point in results.points]

            # Ищем позицию первого релевантного документа
            rank = None
            for i, idx in enumerate(retrieved_idx, start=1):
                if idx in query['idx']:
                    rank = i
                    break

            # Добавляем обратный ранг (или 0 если не нашли)
            if rank:
                sum_reciprocal_ranks += 1.0 / rank
            # else: добавляем 0 (неявно)

        return sum_reciprocal_ranks / total



def main():
    metrics = Metrics(name_model="intfloat/multilingual-e5-small")

    with open("data/datasets/dataset_MiniLM_300_80_0.8.json", "r", encoding='utf-8') as f:
        dataset = json.load(f)

    all_metrics = []

    all_metrics.append(metrics.hits_k(dataset))
    all_metrics.append(metrics.mrr_at_10(dataset))

    for m in all_metrics:
        print(m)

if __name__ == "__main__":
    main()



