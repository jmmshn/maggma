import inspect
from abc import abstractmethod
from typing import Any, Callable, Dict, List, Optional, Tuple

from fastapi.params import Query
from monty.json import MontyDecoder
from pydantic import BaseModel
from pydantic.fields import ModelField

from maggma.api.query_operator import QueryOperator
from maggma.api.utils import STORE_PARAMS
from maggma.utils import dynamic_import


class DynamicQueryOperator(QueryOperator):
    """Abstract Base class for dynamic query operators"""

    def __init__(
        self,
        model: BaseModel,
        fields: Optional[List[str]] = None,
        excluded_fields: Optional[List[str]] = None,
    ):

        self.model = model
        self.fields = fields
        self.excluded_fields = excluded_fields

        all_fields: Dict[str, ModelField] = model.__fields__
        param_fields = fields or list(
            set(all_fields.keys()) - set(excluded_fields or [])
        )

        # Convert the fields into operator tuples
        ops = [
            op
            for name, field in all_fields.items()
            if name in param_fields
            for op in self.field_to_operator(name, field)
        ]

        # Dictionary to make converting the API query names to function that generates
        # Maggma criteria dictionaries
        self.mapping = {op[0]: op[3] for op in ops}

        def query(**kwargs) -> STORE_PARAMS:
            criteria = []
            for k, v in kwargs.items():
                if v is not None:
                    try:
                        criteria.append(self.mapping[k](v))
                    except KeyError:
                        raise KeyError(
                            f"Cannot find key {k} in current query to database mapping"
                        )

            return {"criteria": {k: v for crit in criteria for k, v in crit.items()}}

        # building the signatures for FastAPI Swagger UI
        signatures: List = [
            inspect.Parameter(
                op[0],
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                default=op[2],
                annotation=op[1],
            )
            for op in ops
        ]

        setattr(query, "__signature__", inspect.Signature(signatures))

        self.query = query  # type: ignore

    def query(self):
        " Stub query function for abstract class "
        pass

    @abstractmethod
    def field_to_operator(
        self, name: str, field: ModelField
    ) -> List[Tuple[str, Any, Query, Callable[..., Dict]]]:
        """
        Converts a PyDantic ModelField into a Tuple with the
            - query param name,
            - query param type
            - FastAPI Query object,
            - and callable to convert the value into a query dict
        """
        pass

    @classmethod
    def from_dict(cls, d):
        if isinstance(d["model"], str):
            d["model"] = dynamic_import(d["model"])

        decoder = MontyDecoder()
        return cls(**{k: decoder.process_decoded(v) for k, v in d.items()})

    def as_dict(self) -> Dict:
        """
        Special as_dict implemented to convert pydantic models into strings
        """
        d = super().as_dict()  # Ensures sub-classes serialize correctly
        d["model"] = f"{self.model.__module__}.{self.model.__name__}"  # type: ignore
        return d


class NumericQuery(DynamicQueryOperator):
    " Query Operator to enable searching on numeric fields"

    def field_to_operator(
        self, name: str, field: ModelField
    ) -> List[Tuple[str, Any, Query, Callable[..., Dict]]]:

        """
        Converts a PyDantic ModelField into a Tuple with the
        query_param name,
        default value,
        Query object,
        and callable to convert it into a query dict
        """

        ops = []
        field_type = field.type_

        if field_type in [int, float]:
            title: str = field.field_info.title or field.name

            ops = [
                (
                    f"{field.name}_lt",
                    field_type,
                    Query(
                        default=None,
                        description=f"Querying for {title} is less than a value",
                    ),
                    lambda val: {f"{field.name}": {"$lt": val}},
                ),
                (
                    f"{field.name}_gt",
                    field_type,
                    Query(
                        default=None,
                        description=f"Querying for {title} is greater than a value",
                    ),
                    lambda val: {f"{field.name}": {"$gt": val}},
                ),
            ]

        if field_type is int:
            ops.extend(
                [
                    (
                        f"{field.name}",
                        field_type,
                        Query(
                            default=None,
                            description=f"Querying for {title} is equal to a value",
                        ),
                        lambda val: {f"{field.name}": val},
                    ),
                    (
                        f"{field.name}_not_eq",
                        field_type,
                        Query(
                            default=None,
                            description=f"Querying for {title} is not equal to a value",
                        ),
                        lambda val: {f"{field.name}": {"$ne": val}},
                    ),
                    (
                        f"{field.name}_eq_any",
                        List[field_type],  # type: ignore
                        Query(
                            default=None,
                            description=f"Querying for {title} is any of these values",
                        ),
                        lambda val: {f"{field.name}": {"$in": val}},
                    ),
                    (
                        f"{field.name}_neq_any",
                        List[field_type],  # type: ignore
                        Query(
                            default=None,
                            description=f"Querying for {title} is not any of these values",
                        ),
                        lambda val: {f"{field.name}": {"$nin": val}},
                    ),
                ]
            )

        return ops


class StringQueryOperator(DynamicQueryOperator):
    " Query Operator to enable searching on numeric fields"

    def field_to_operator(
        self, name: str, field: ModelField
    ) -> List[Tuple[str, Any, Query, Callable[..., Dict]]]:

        """
        Converts a PyDantic ModelField into a Tuple with the
        query_param name,
        default value,
        Query object,
        and callable to convert it into a query dict
        """

        ops = []
        field_type: type = field.type_

        if field_type in [str]:
            title: str = field.field_info.title or field.name

            ops = [
                (
                    f"{field.name}",
                    field_type,
                    Query(
                        default=None,
                        description=f"Query for {title} is equal to a value",
                    ),
                    lambda val: {f"{field.name}": val},
                ),
                (
                    f"{field.name}_not_eq",
                    field_type,
                    Query(
                        default=None,
                        description=f"Querying for {title} is not equal to a value",
                    ),
                    lambda val: {f"{field.name}": {"$ne": val}},
                ),
                (
                    f"{field.name}_eq_any",
                    List[field_type],  # type: ignore
                    Query(
                        default=None,
                        description=f"Querying for {title} is any of these values",
                    ),
                    lambda val: {f"{field.name}": {"$in": val}},
                ),
                (
                    f"{field.name}_neq_any",
                    List[field_type],  # type: ignore
                    Query(
                        default=None,
                        description=f"Querying for {title} is not any of these values",
                    ),
                    lambda val: {f"{field.name}": {"$nin": val}},
                ),
            ]

        return ops
