from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from whiskerrag_types.model import Knowledge, PageResponse, Tenant
from whiskerrag_types.model.knowledge import (EmbeddingModelEnum,
                                              KnowledgeSourceEnum,
                                              KnowledgeTypeEnum)

from api.knowledge.utils import (_is_knowledge_saved,
                                 _process_single_knowledge, gen_knowledge_list)


# Test fixtures
@pytest.fixture
def mock_tenant():
    """Create a mock tenant for testing"""
    return Tenant(
        tenant_id="test-tenant-id",
        tenant_name="Test Tenant",
        email="test@example.com",
        secret_key="test-secret",
        is_active=True,
    )


@pytest.fixture
def mock_knowledge_create():
    """Create a mock knowledge create object"""
    mock = MagicMock()
    mock.space_id = "test-space"
    mock.knowledge_name = "test-doc"
    mock.knowledge_type = KnowledgeTypeEnum.TEXT
    mock.source_type = KnowledgeSourceEnum.USER_INPUT_TEXT
    mock.model_dump.return_value = {
        "space_id": "test-space",
        "knowledge_name": "test-doc",
        "knowledge_type": KnowledgeTypeEnum.TEXT,
        "source_type": KnowledgeSourceEnum.USER_INPUT_TEXT,
        "source_config": {},
        "embedding_model_name": EmbeddingModelEnum.OPENAI,
        "split_config": {"type": "text", "chunk_size": 500},
        "file_sha": "test-sha",
    }
    return mock


@pytest.fixture
def mock_knowledge():
    """Create a mock knowledge object"""
    return Knowledge(
        knowledge_id="test-knowledge-id",
        space_id="test-space",
        knowledge_type=KnowledgeTypeEnum.TEXT,
        knowledge_name="test-doc",
        source_type=KnowledgeSourceEnum.USER_INPUT_TEXT,
        source_config={},
        embedding_model_name=EmbeddingModelEnum.OPENAI,
        split_config={"type": "text", "chunk_size": 500},
        file_sha="test-sha",
        tenant_id="test-tenant-id",
    )


@pytest.fixture
def mock_db_engine():
    """Create a mock database engine"""
    mock_engine = AsyncMock()
    mock_engine.get_knowledge_list = AsyncMock()
    mock_engine.delete_knowledge = AsyncMock()
    return mock_engine


class TestGenKnowledgeList:
    """Test cases for gen_knowledge_list function"""

    @pytest.mark.asyncio
    async def test_gen_knowledge_list_empty_input(self, mock_tenant):
        """Test gen_knowledge_list with empty input"""
        result = await gen_knowledge_list([], mock_tenant)
        assert result == []

    @pytest.mark.asyncio
    async def test_gen_knowledge_list_none_input(self, mock_tenant):
        """Test gen_knowledge_list with None input"""
        result = await gen_knowledge_list(None, mock_tenant)
        assert result == []

    @pytest.mark.asyncio
    @patch("api.knowledge.utils.PluginManager")
    async def test_gen_knowledge_list_single_new_knowledge(
        self, mock_plugin_manager, mock_tenant, mock_knowledge_create, mock_db_engine
    ):
        """Test gen_knowledge_list with a single new knowledge that should be added"""
        # Setup mocks
        mock_plugin_manager.return_value.dbPlugin = mock_db_engine

        # Mock _is_knowledge_saved to return None (knowledge doesn't exist)
        mock_db_engine.get_knowledge_list.return_value = PageResponse(
            items=[], total=0, page=1, page_size=10, total_pages=0
        )

        result = await gen_knowledge_list([mock_knowledge_create], mock_tenant)

        assert len(result) == 1
        assert result[0].tenant_id == mock_tenant.tenant_id
        assert result[0].knowledge_name == "test-doc"

    @pytest.mark.asyncio
    @patch("api.knowledge.utils.PluginManager")
    async def test_gen_knowledge_list_existing_knowledge_same_sha(
        self, mock_plugin_manager, mock_tenant, mock_knowledge, mock_db_engine
    ):
        """Test gen_knowledge_list with existing knowledge with same file_sha (should skip)"""
        # Setup mocks
        mock_plugin_manager.return_value.dbPlugin = mock_db_engine

        # Create mock knowledge create with same SHA
        mock_knowledge_create = MagicMock()
        mock_knowledge_create.space_id = "test-space"
        mock_knowledge_create.knowledge_name = "test-doc"
        mock_knowledge_create.knowledge_type = KnowledgeTypeEnum.TEXT
        mock_knowledge_create.source_type = KnowledgeSourceEnum.USER_INPUT_TEXT
        mock_knowledge_create.model_dump.return_value = {
            "space_id": "test-space",
            "knowledge_name": "test-doc",
            "knowledge_type": KnowledgeTypeEnum.TEXT,
            "source_type": KnowledgeSourceEnum.USER_INPUT_TEXT,
            "source_config": {},
            "embedding_model_name": EmbeddingModelEnum.OPENAI,
            "split_config": {"type": "text", "chunk_size": 500},
            "file_sha": "same-sha",
        }

        # Mock existing knowledge with same file_sha
        existing_knowledge = mock_knowledge
        existing_knowledge.file_sha = "same-sha"
        mock_db_engine.get_knowledge_list.return_value = PageResponse(
            items=[existing_knowledge], total=1, page=1, page_size=10, total_pages=1
        )

        result = await gen_knowledge_list([mock_knowledge_create], mock_tenant)

        assert len(result) == 0  # Should skip existing knowledge with same SHA

    @pytest.mark.asyncio
    @patch("api.knowledge.utils.PluginManager")
    async def test_gen_knowledge_list_existing_knowledge_different_sha(
        self, mock_plugin_manager, mock_tenant, mock_knowledge, mock_db_engine
    ):
        """Test gen_knowledge_list with existing knowledge with different file_sha (should update)"""
        # Setup mocks
        mock_plugin_manager.return_value.dbPlugin = mock_db_engine

        # Create mock knowledge create with different SHA
        mock_knowledge_create = MagicMock()
        mock_knowledge_create.space_id = "test-space"
        mock_knowledge_create.knowledge_name = "test-doc"
        mock_knowledge_create.knowledge_type = KnowledgeTypeEnum.TEXT
        mock_knowledge_create.source_type = KnowledgeSourceEnum.USER_INPUT_TEXT
        mock_knowledge_create.model_dump.return_value = {
            "space_id": "test-space",
            "knowledge_name": "test-doc",
            "knowledge_type": KnowledgeTypeEnum.TEXT,
            "source_type": KnowledgeSourceEnum.USER_INPUT_TEXT,
            "source_config": {},
            "embedding_model_name": EmbeddingModelEnum.OPENAI,
            "split_config": {"type": "text", "chunk_size": 500},
            "file_sha": "new-sha",
        }

        # Mock existing knowledge with different file_sha
        existing_knowledge = mock_knowledge
        existing_knowledge.file_sha = "old-sha"
        mock_db_engine.get_knowledge_list.return_value = PageResponse(
            items=[existing_knowledge], total=1, page=1, page_size=10, total_pages=1
        )

        result = await gen_knowledge_list([mock_knowledge_create], mock_tenant)

        assert len(result) == 1
        assert result[0].file_sha == "new-sha"
        # Should have called delete_knowledge for the old version
        mock_db_engine.delete_knowledge.assert_called_once_with(
            mock_tenant.tenant_id, [existing_knowledge.knowledge_id]
        )

    @pytest.mark.asyncio
    @patch("api.knowledge.utils.PluginManager")
    async def test_gen_knowledge_list_multiple_knowledge_mixed_scenarios(
        self, mock_plugin_manager, mock_tenant, mock_db_engine
    ):
        """Test gen_knowledge_list with multiple knowledge items in different scenarios"""
        # Setup mocks
        mock_plugin_manager.return_value.dbPlugin = mock_db_engine

        # Create multiple knowledge create objects
        knowledge_creates = []
        for i in range(3):
            mock_create = MagicMock()
            mock_create.space_id = f"test-space-{i}"
            mock_create.knowledge_name = f"test-doc-{i}"
            mock_create.knowledge_type = KnowledgeTypeEnum.TEXT
            mock_create.source_type = KnowledgeSourceEnum.USER_INPUT_TEXT
            mock_create.model_dump.return_value = {
                "space_id": f"test-space-{i}",
                "knowledge_name": f"test-doc-{i}",
                "knowledge_type": KnowledgeTypeEnum.TEXT,
                "source_type": KnowledgeSourceEnum.USER_INPUT_TEXT,
                "source_config": {},
                "embedding_model_name": EmbeddingModelEnum.OPENAI,
                "split_config": {"type": "text", "chunk_size": 500},
                "file_sha": f"sha-{i}",
            }
            knowledge_creates.append(mock_create)

        # Mock different scenarios for each knowledge
        def mock_get_knowledge_list(tenant_id, page_params):
            eq_conditions = page_params.eq_conditions
            if eq_conditions["knowledge_name"] == "test-doc-0":
                # First one: new knowledge
                return PageResponse(
                    items=[], total=0, page=1, page_size=10, total_pages=0
                )
            elif eq_conditions["knowledge_name"] == "test-doc-1":
                # Second one: existing with same SHA (skip)
                existing = Knowledge(
                    knowledge_id="existing-1",
                    space_id="test-space-1",
                    knowledge_name="test-doc-1",
                    knowledge_type=KnowledgeTypeEnum.TEXT,
                    source_type=KnowledgeSourceEnum.USER_INPUT_TEXT,
                    source_config={},
                    embedding_model_name=EmbeddingModelEnum.OPENAI,
                    split_config={"type": "text", "chunk_size": 500},
                    file_sha="sha-1",
                    tenant_id=tenant_id,
                )
                return PageResponse(
                    items=[existing], total=1, page=1, page_size=10, total_pages=1
                )
            else:
                # Third one: existing with different SHA (update)
                existing = Knowledge(
                    knowledge_id="existing-2",
                    space_id="test-space-2",
                    knowledge_name="test-doc-2",
                    knowledge_type=KnowledgeTypeEnum.TEXT,
                    source_type=KnowledgeSourceEnum.USER_INPUT_TEXT,
                    source_config={},
                    embedding_model_name=EmbeddingModelEnum.OPENAI,
                    split_config={"type": "text", "chunk_size": 500},
                    file_sha="old-sha-2",
                    tenant_id=tenant_id,
                )
                return PageResponse(
                    items=[existing], total=1, page=1, page_size=10, total_pages=1
                )

        mock_db_engine.get_knowledge_list.side_effect = mock_get_knowledge_list

        result = await gen_knowledge_list(knowledge_creates, mock_tenant)

        # Should return 2 items (new one + updated one, skip the same SHA one)
        assert len(result) == 2
        knowledge_names = [k.knowledge_name for k in result]
        assert "test-doc-0" in knowledge_names  # New knowledge
        assert "test-doc-2" in knowledge_names  # Updated knowledge
        assert "test-doc-1" not in knowledge_names  # Skipped knowledge

    @pytest.mark.asyncio
    @patch("api.knowledge.utils.PluginManager")
    async def test_gen_knowledge_list_exception_handling(
        self, mock_plugin_manager, mock_tenant, mock_knowledge_create, mock_db_engine
    ):
        """Test gen_knowledge_list exception handling"""
        # Setup mocks to raise exception
        mock_plugin_manager.return_value.dbPlugin = mock_db_engine
        mock_db_engine.get_knowledge_list.side_effect = Exception("Database error")

        with pytest.raises(Exception, match="Database error"):
            await gen_knowledge_list([mock_knowledge_create], mock_tenant)


class TestProcessSingleKnowledge:
    """Test cases for _process_single_knowledge function"""

    @pytest.mark.asyncio
    @patch("api.knowledge.utils._is_knowledge_saved")
    @patch("api.knowledge.utils.KNOWLEDGE_CREATE_2_KNOWLEDGE_STRATEGY_MAP", {})
    async def test_process_single_knowledge_new_knowledge(
        self,
        mock_is_knowledge_saved,
        mock_tenant,
        mock_knowledge_create,
        mock_db_engine,
    ):
        """Test _process_single_knowledge with new knowledge"""
        mock_is_knowledge_saved.return_value = None

        result = await _process_single_knowledge(
            mock_knowledge_create, mock_tenant, mock_db_engine
        )

        assert result is not None
        assert result.tenant_id == mock_tenant.tenant_id

    @pytest.mark.asyncio
    @patch("api.knowledge.utils._is_knowledge_saved")
    @patch("api.knowledge.utils.KNOWLEDGE_CREATE_2_KNOWLEDGE_STRATEGY_MAP", {})
    async def test_process_single_knowledge_existing_same_sha(
        self, mock_is_knowledge_saved, mock_tenant, mock_knowledge, mock_db_engine
    ):
        """Test _process_single_knowledge with existing knowledge having same SHA"""
        mock_knowledge.file_sha = "same-sha"
        mock_is_knowledge_saved.return_value = mock_knowledge

        # Create mock knowledge create with same SHA
        mock_knowledge_create = MagicMock()
        mock_knowledge_create.model_dump.return_value = {
            "space_id": "test-space",
            "knowledge_name": "test-doc",
            "knowledge_type": KnowledgeTypeEnum.TEXT,
            "source_type": KnowledgeSourceEnum.USER_INPUT_TEXT,
            "source_config": {},
            "embedding_model_name": EmbeddingModelEnum.OPENAI,
            "split_config": {"type": "text", "chunk_size": 500},
            "file_sha": "same-sha",
        }

        result = await _process_single_knowledge(
            mock_knowledge_create, mock_tenant, mock_db_engine
        )

        assert result is None  # Should return None for same SHA

    @pytest.mark.asyncio
    @patch("api.knowledge.utils._is_knowledge_saved")
    @patch("api.knowledge.utils.KNOWLEDGE_CREATE_2_KNOWLEDGE_STRATEGY_MAP", {})
    async def test_process_single_knowledge_existing_different_sha(
        self, mock_is_knowledge_saved, mock_tenant, mock_knowledge, mock_db_engine
    ):
        """Test _process_single_knowledge with existing knowledge having different SHA"""
        mock_knowledge.file_sha = "old-sha"
        mock_is_knowledge_saved.return_value = mock_knowledge

        # Create mock knowledge create with different SHA
        mock_knowledge_create = MagicMock()
        mock_knowledge_create.model_dump.return_value = {
            "space_id": "test-space",
            "knowledge_name": "test-doc",
            "knowledge_type": KnowledgeTypeEnum.TEXT,
            "source_type": KnowledgeSourceEnum.USER_INPUT_TEXT,
            "source_config": {},
            "embedding_model_name": EmbeddingModelEnum.OPENAI,
            "split_config": {"type": "text", "chunk_size": 500},
            "file_sha": "new-sha",
        }

        result = await _process_single_knowledge(
            mock_knowledge_create, mock_tenant, mock_db_engine
        )

        assert result is not None
        assert result.file_sha == "new-sha"
        # Should have called delete for old knowledge
        mock_db_engine.delete_knowledge.assert_called_once_with(
            mock_tenant.tenant_id, [mock_knowledge.knowledge_id]
        )


class TestIsKnowledgeSaved:
    """Test cases for _is_knowledge_saved function"""

    @pytest.mark.asyncio
    @patch("api.knowledge.utils.PluginManager")
    async def test_is_knowledge_saved_exists(
        self, mock_plugin_manager, mock_tenant, mock_knowledge, mock_db_engine
    ):
        """Test _is_knowledge_saved when knowledge exists"""
        mock_plugin_manager.return_value.dbPlugin = mock_db_engine

        # Create mock knowledge create
        mock_knowledge_create = MagicMock()
        mock_knowledge_create.space_id = "test-space"
        mock_knowledge_create.knowledge_name = "test-doc"
        mock_knowledge_create.knowledge_type = KnowledgeTypeEnum.TEXT
        mock_knowledge_create.source_type = KnowledgeSourceEnum.USER_INPUT_TEXT

        mock_db_engine.get_knowledge_list.return_value = PageResponse(
            items=[mock_knowledge], total=1, page=1, page_size=10, total_pages=1
        )

        result = await _is_knowledge_saved(mock_knowledge_create, mock_tenant)

        assert result == mock_knowledge

    @pytest.mark.asyncio
    @patch("api.knowledge.utils.PluginManager")
    async def test_is_knowledge_saved_not_exists(
        self, mock_plugin_manager, mock_tenant, mock_db_engine
    ):
        """Test _is_knowledge_saved when knowledge doesn't exist"""
        mock_plugin_manager.return_value.dbPlugin = mock_db_engine

        # Create mock knowledge create
        mock_knowledge_create = MagicMock()
        mock_knowledge_create.space_id = "test-space"
        mock_knowledge_create.knowledge_name = "test-doc"
        mock_knowledge_create.knowledge_type = KnowledgeTypeEnum.TEXT
        mock_knowledge_create.source_type = KnowledgeSourceEnum.USER_INPUT_TEXT

        mock_db_engine.get_knowledge_list.return_value = PageResponse(
            items=[], total=0, page=1, page_size=10, total_pages=0
        )

        result = await _is_knowledge_saved(mock_knowledge_create, mock_tenant)

        assert result is None
