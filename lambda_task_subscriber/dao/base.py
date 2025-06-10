import json
import math
import os
from enum import Enum
from typing import Any, List

from dotenv import load_dotenv
from pydantic import BaseModel
from supabase.client import Client, create_client


def load_env():
    load_dotenv(verbose=True, override=True)
    load_dotenv(dotenv_path=".env.local", verbose=True, override=True)


load_env()


# Define a method to load an environmental variable and return its value
def get_env_variable(key: str, default=None):
    # Get the environment variable, returning the default value if it does not exist
    return os.getenv(key, default)


supabase_url = get_env_variable("SUPABASE_URL")
supabase_key = get_env_variable("SUPABASE_SERVICE_KEY")


def get_client():
    supabase: Client = create_client(supabase_url, supabase_key)
    return supabase


class BaseDAO:
    client: Client = get_client()

    async def _get_all_paginated_data(
        self, tenant_id: str, table_name: str, model_cls: Any, eq_conditions: dict
    ) -> List[Any]:
        page_size = 100
        all_items: List[Any] = []

        # First, create base query for total count
        count_query = self.client.table(table_name).select("count")
        count_query = count_query.eq("tenant_id", tenant_id)

        # Apply eq_conditions for count query
        for field, value in eq_conditions.items():
            if isinstance(value, Enum):
                value = value.value
            elif isinstance(
                value, BaseModel
            ):  # Assuming BaseModel is imported and available (e.g., from pydantic)
                value = value.model_dump()
                count_query = count_query.filter(field, "eq", json.dumps(value))
                continue
            count_query = count_query.eq(field, value)

        count_res = count_query.execute()
        total_count = count_res.data[0]["count"]

        if total_count == 0:
            return []

        total_pages = math.ceil(total_count / page_size)

        for page in range(1, total_pages + 1):
            offset = (page - 1) * page_size
            limit = page_size

            # Create a base query for fetching data
            data_query = self.client.table(table_name).select("*")
            data_query = data_query.eq("tenant_id", tenant_id)

            # Apply eq_conditions for data query
            for field, value in eq_conditions.items():
                if isinstance(value, Enum):
                    value = value.value
                elif isinstance(
                    value, BaseModel
                ):  # Assuming BaseModel is imported and available (e.g., from pydantic)
                    value = value.model_dump()
                    data_query = data_query.filter(field, "eq", json.dumps(value))
                    continue
                data_query = data_query.eq(field, value)

            res = data_query.range(
                offset, offset + limit - 1
            ).execute()  # Supabase range is inclusive
            if res.data:
                all_items.extend([model_cls(**item) for item in res.data])
        return all_items
