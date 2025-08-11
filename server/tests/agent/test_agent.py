from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.responses import StreamingResponse

from api.agent.router import ProResearchRequest, pro_research


@pytest.fixture
def mock_db_engine():
    db_engine = MagicMock()
    db_engine.agent_invoke = AsyncMock(return_value=iter([b"test"]))
    return db_engine


@pytest.mark.asyncio
async def test_pro_research(mock_db_engine):
    input_body = {
        "messages": [{"role": "user", "content": "如何升级到 bigfish 4"}],
        "model": "wohu_qwen3_235b_a22b",
        "number_of_initial_queries": 3,
        "max_research_loops": 2,
        "enable_knowledge_retrieval": True,
        "enable_web_search": False,
        "knowledge_scope_list": [
            {
                "space_ids": ["123", "456"],
                "tenant_id": "123",
                "auth_info": "123",
            }
        ],
        "knowledge_retrieval_config": {
            "type": "deep_retrieval",
        },
    }

    # 创建一个 mock 的 body
    body = ProResearchRequest(**input_body)

    # Mock PluginManager 和它的 dbPlugin
    with patch("api.agent.router.PluginManager") as mock_plugin_manager:
        mock_instance = MagicMock()
        mock_instance.dbPlugin = mock_db_engine
        mock_plugin_manager.return_value = mock_instance

        # 调用 pro_research 接口
        response = await pro_research(body)

        # 断言 response 的类型是 StreamingResponse
        assert isinstance(response, StreamingResponse)

        # 验证 dbPlugin.agent_invoke 被调用了
        mock_db_engine.agent_invoke.assert_called_once_with(body)
