from server.supabase_aws_plugin.db_engine.supabase_client import SupaBasePlugin


class MockPlugin(SupaBasePlugin):
    retrieval_count: dict[str, int] = {}

    def get_db_client(self) -> None:
        pass

    async def init(self) -> None:
        print("mock plugin init")

    async def cleanup(self) -> None:
        pass

    async def batch_update_knowledge_retrieval_count(
        self, knowledge_id_list: dict[str, int]
    ) -> None:
        for knowledge_id, count in knowledge_id_list.items():
            if knowledge_id in self.retrieval_count:
                self.retrieval_count[knowledge_id] += count
            else:
                self.retrieval_count[knowledge_id] = count

    def reset_retrieval_count(self):
        self.retrieval_count.clear()
