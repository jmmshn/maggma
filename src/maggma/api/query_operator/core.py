from abc import abstractmethod
from typing import Dict
from monty.json import MSONable


from maggma.api.util import STORE_PARAMS


class QueryOperator(MSONable):
    """
    Base Query Operator class for defining powerfull query language
    in the Materials API
    """

    @abstractmethod
    def query(self) -> STORE_PARAMS:
        """
        The query function that does the work for this query operator
        """

    def meta(self) -> Dict:
        """
        Returns meta data to return with the Response

        Args:
            store: the Maggma Store that the resource uses
            query: the query being executed in this API call
        """
        return {}

    def post_process(self, doc: Dict) -> Dict:
        """
        An optional post-processing function for the data
        """
        return doc
