"""Role overlays read off the source map (v0.2 §16).

The data itself comes from the diagram, so what these guard is the link to our own
tree: a renamed node must not silently drop out of a role.
"""

from __future__ import annotations

from app import tree_content


def _tree_nodes() -> set[str]:
    tree = tree_content.load_tree_file()
    return {node["id"] for block in tree["blocks"] for node in block["nodes"]}


def test_roles_validate_against_the_tree():
    roles = tree_content.load_roles_file()
    assert tree_content.validate_roles(roles, tree_content.load_tree_file()) == []


def test_product_manager_spans_the_whole_map():
    roles = tree_content.load_roles_file()
    pm = next(r for r in roles["roles"] if r["key"] == "product_manager")
    assert set(pm["nodeIds"]) == _tree_nodes()


def test_every_specialised_role_has_nodes_and_leaves_some_out():
    roles = tree_content.load_roles_file()
    everything = _tree_nodes()
    specialised = [r for r in roles["roles"] if r["key"] != "product_manager"]
    assert len(specialised) == 9
    for role in specialised:
        ids = set(role["nodeIds"])
        assert ids, f"{role['key']} has no nodes"
        assert ids < everything, f"{role['key']} covers the whole map, which is Product Manager"


def test_roles_name_their_source():
    roles = tree_content.load_roles_file()
    assert "productframework.ru" in roles["sourceAttribution"]
