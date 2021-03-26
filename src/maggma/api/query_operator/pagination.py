import inspect
import warnings
from typing import Dict, Optional

from fastapi import Query
from maggma.api.util import STORE_PARAMS
from maggma.api.query_operator import QueryOperator


class PaginationQuery(QueryOperator):
    """Query opertators to provides Pagination"""

    def __init__(
        self, default_skip: int = 0, default_limit: int = 10, max_limit: int = 100
    ):
        """
        Args:
            default_skip: the default number of documents to skip
            default_limit: the default number of documents to return
            max_limit: max number of documents to return
        """
        self.default_skip = default_skip
        self.default_limit = default_limit
        self.max_limit = max_limit

        def query(
            skip: int = Query(
                default_skip, description="Number of entries to skip in the search"
            ),
            limit: int = Query(
                default_limit,
                description="Max number of entries to return in a single query."
                f" Limited to {max_limit}",
            ),
        ) -> STORE_PARAMS:
            """
            Pagination parameters for the API Endpoint
            """
            if limit > max_limit:
                raise Exception(
                    "Requested more data per query than allowed by this endpoint."
                    f"The max limit is {max_limit} entries"
                )
            return {"skip": skip, "limit": limit}

        self.query = query  # type: ignore

    def meta(self) -> Dict:
        """
        Metadata for the pagination params
        """
        return {"max_limit": self.max_limit}
