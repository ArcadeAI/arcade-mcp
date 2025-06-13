from arcade_core.schema import FullyQualifiedName, ToolkitDefinition


def test_initialization():
    fqn = FullyQualifiedName("Tool1", "Toolkit1", "1.0")
    assert fqn.name == "Tool1"
    assert fqn.toolkit_name == "Toolkit1"
    assert fqn.toolkit_version == "1.0"


def test_str():
    fqn = FullyQualifiedName("Tool1", "Toolkit1", "1.0")
    assert str(fqn) == "Toolkit1.Tool1"


def test_equality():
    fqn1 = FullyQualifiedName("Tool1", "Toolkit1", "1.0")
    fqn2 = FullyQualifiedName("Tool1", "Toolkit1", "1.0")
    fqn3 = FullyQualifiedName("Tool2", "Toolkit1", "1.0")
    assert fqn1 == fqn2
    assert fqn1 != fqn3


def test_equality_ignoring_version():
    fqn1 = FullyQualifiedName("Tool1", "Toolkit1", "1.0")
    fqn2 = FullyQualifiedName("Tool1", "Toolkit1", "2.0")
    assert fqn1.equals_ignoring_version(fqn2)


def test_ftqn_case_insensitivity():
    fqn1 = FullyQualifiedName("Tool1", "Toolkit1", "latest")
    fqn2 = FullyQualifiedName("TOOL1", "toolKit1", "LATEST")
    assert fqn1 == fqn2


def test_hash():
    fqn1 = FullyQualifiedName("Tool1", "Toolkit1", "1.0")
    fqn2 = FullyQualifiedName("TOOL1", "toolkit1", "1.0")
    fqn3 = FullyQualifiedName("Tool2", "Toolkit1", "1.0")
    fqn_set = {fqn1, fqn2, fqn3}
    assert len(fqn_set) == 2


def test_from_toolkit():
    toolkit = ToolkitDefinition(name="toolkit1", version="1.0")
    fqn = FullyQualifiedName.from_toolkit("Tool1", toolkit)
    assert fqn.name == "Tool1"
    assert fqn.toolkit_name == "toolkit1"
    assert fqn.toolkit_version == "1.0"
