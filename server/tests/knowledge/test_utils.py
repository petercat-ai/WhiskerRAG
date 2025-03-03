from whiskerrag_types.model import (
    Knowledge,
    GithubRepoSourceConfig,
    KnowledgeSplitConfig,
)

from server.api.knowledge.utils import get_diff_knowledge_by_sha


def test_get_diff_knowledge_lists_empty_lists():
    result = get_diff_knowledge_by_sha([], [])
    assert result["to_add"] == []
    assert result["to_delete"] == []
    assert result["unchanged"] == []


def test_get_diff_knowledge_lists_no_changes():
    knowledge_item = Knowledge(
        file_sha="123",
        knowledge_name="test",
        tenant_id="test_id",
        space_id="test_space",
        source_config=GithubRepoSourceConfig(
            repo_name="repo_name",
        ),
        split_config=KnowledgeSplitConfig(chunk_size=100, chunk_overlap=50),
    )
    result = get_diff_knowledge_by_sha([knowledge_item], [knowledge_item])
    assert result["to_add"] == []
    assert result["to_delete"] == []
    assert result["unchanged"][0].file_sha == knowledge_item.file_sha


def test_get_diff_knowledge_lists_to_add():
    knowledge_item = Knowledge(
        file_sha="123",
        knowledge_name="test",
        tenant_id="test_id",
        space_id="test_space",
        source_config=GithubRepoSourceConfig(
            repo_name="repo_name",
        ),
        split_config=KnowledgeSplitConfig(chunk_size=100, chunk_overlap=50),
    )
    result = get_diff_knowledge_by_sha([], [knowledge_item])
    assert result["to_add"][0].file_sha == knowledge_item.file_sha
    assert result["to_delete"] == []
    assert result["unchanged"] == []


def test_get_diff_knowledge_lists_to_delete():
    knowledge_item = Knowledge(
        file_sha="123",
        knowledge_name="test",
        tenant_id="test_id",
        space_id="test_space",
        source_config=GithubRepoSourceConfig(
            repo_name="repo_name",
        ),
        split_config=KnowledgeSplitConfig(chunk_size=100, chunk_overlap=50),
    )
    result = get_diff_knowledge_by_sha([knowledge_item], [])
    assert result["to_add"] == []
    assert result["to_delete"][0].file_sha == knowledge_item.file_sha
    assert result["unchanged"] == []


def test_get_diff_knowledge_lists_mixed():
    knowledge_item1 = Knowledge(
        file_sha="123",
        knowledge_name="test1",
        tenant_id="test_id",
        space_id="test_space",
        source_config=GithubRepoSourceConfig(
            repo_name="repo_name",
        ),
        split_config=KnowledgeSplitConfig(chunk_size=100, chunk_overlap=50),
    )
    knowledge_item2 = Knowledge(
        file_sha="456",
        knowledge_name="test2",
        tenant_id="test_id",
        space_id="test_space",
        source_config=GithubRepoSourceConfig(
            repo_name="repo_name",
        ),
        split_config=KnowledgeSplitConfig(chunk_size=100, chunk_overlap=50),
    )
    knowledge_item3 = Knowledge(
        file_sha="789",
        knowledge_name="test3",
        tenant_id="test_id",
        space_id="test_space",
        source_config=GithubRepoSourceConfig(
            repo_name="repo_name",
        ),
        split_config=KnowledgeSplitConfig(chunk_size=100, chunk_overlap=50),
    )
    result = get_diff_knowledge_by_sha(
        [knowledge_item1, knowledge_item2], [knowledge_item2, knowledge_item3]
    )
    assert result["to_add"][0].file_sha == knowledge_item3.file_sha
    assert result["to_delete"][0].file_sha == knowledge_item1.file_sha
    assert result["unchanged"][0].file_sha == knowledge_item2.file_sha
