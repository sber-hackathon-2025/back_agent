import os
from enum import Enum
from gigachat import GigaChat
from dotenv import load_dotenv

load_dotenv(override=True)

GIGA_CREDS = os.getenv("GIGA_CREDS")


class QueryTypeEnum(Enum):
    text = "text"
    code = "code"
    all = "all"


class TargetEnum(Enum):
    function = "function"
    object = "object"
    repository = "repository"
    all = "all"


class Candidate:
    ...


class SimilarCodeAgent:
    def __init__(self, query: str, query_type: QueryTypeEnum, target_type: TargetEnum):
        self.query = query
        self.detailed_query = None
        self.query_type = query_type
        self.target_type = target_type

    def detail_query(self, giga_client: GigaChat) -> None:
        self.detailed_query = (
            giga_client.chat(f"Опиши это в 10 предложениях: {self.query}")
            .choices[0]
            .message.content
        )

    def get_vector(self, giga_client: GigaChat) -> list[float]:
        response = giga_client.embeddings([self.detailed_query])
        return response.data[0].embeddings

    def find_candidates(self, get_candidates: list[float]) -> list[list[float]]: ...

    def get_candidates(
        self, vectorized_candidates: list[list[float]]
    ) -> list[Candidate]: ...

    def find_similar(self) -> (int, list[Candidate]):
        try:
            with GigaChat(credentials=GIGA_CREDS, verify_ssl_certs=False) as giga_client:
                self.detail_query(giga_client)
                query_vector = self.get_vector(giga_client)

            vectorized_candidates = self.find_candidates(query_vector)

            candidates: list[Candidate] = self.get_candidates(vectorized_candidates)

            return 200, candidates
        except Exception:
            return 400, []
