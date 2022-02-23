from typing import Any, Dict, List, Tuple

from shillelagh.backends.apsw.dialects.base import APSWDialect
from shillelagh.backends.apsw.dialects.gsheets import extract_query
from sqlalchemy.engine import Connection
from sqlalchemy.engine.url import URL

from .lib import run_query

# -----------------------------------------------------------------------------


class APSWGraphQLDialect(APSWDialect):
    supports_statement_cache = False

    def __init__(
        self,
        **kwargs: Any,
    ):
        super().__init__(safe=True, adapters=["graphql"], **kwargs)

    def get_table_names(
        self, connection: Connection, schema: str = None, **kwargs: Any
    ) -> List[str]:
        graphql_api = self.db_url_to_graphql_api(connection.engine.url)

        query = """{
  __schema {
    queryType {
      fields {
        name
      }
    }
  }
}"""
        data = run_query(graphql_api, query=query)

        # TODO(cancan101): filter out "non-Array" returns
        # This is tricky as Connections are non-Array
        return [field["name"] for field in data["__schema"]["queryType"]["fields"]]

    def db_url_to_graphql_api(self, url: URL) -> str:
        query = extract_query(url)
        is_https = query.get("is_https", "1") != "0"
        proto = "https" if is_https else "http"
        port_str = "" if url.port is None else f":{url.port}"
        return f"{proto}://{url.host}{port_str}/{url.database}"

    def create_connect_args(
        self,
        url: URL,
    ) -> Tuple[Tuple[()], Dict[str, Any]]:
        args, kwargs = super().create_connect_args(url)

        if "adapter_kwargs" in kwargs and kwargs["adapter_kwargs"] != {}:
            raise ValueError(
                f"Unexpected adapter_kwargs found: {kwargs['adapter_kwargs']}"
            )

        adapter_kwargs = {"graphql": {"graphql_api": self.db_url_to_graphql_api(url)}}

        # this seems gross, esp the path override. unclear why memory has to be set here
        return args, {**kwargs, "path": ":memory:", "adapter_kwargs": adapter_kwargs}
