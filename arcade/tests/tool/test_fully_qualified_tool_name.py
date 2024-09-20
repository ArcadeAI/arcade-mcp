from arcade.core.schema import FullyQualifiedToolName, ToolkitDefinition


def test_initialization():
    fqtn = FullyQualifiedToolName("Tool1", "Toolkit1", "1.0")
    assert fqtn.name == "Tool1"
    assert fqtn.toolkit_name == "Toolkit1"
    assert fqtn.toolkit_version == "1.0"


def test_str():
    fqtn = FullyQualifiedToolName("Tool1", "Toolkit1", "1.0")
    assert str(fqtn) == "Toolkit1.Tool1"


def test_equality():
    fqtn1 = FullyQualifiedToolName("Tool1", "Toolkit1", "1.0")
    fqtn2 = FullyQualifiedToolName("Tool1", "Toolkit1", "1.0")
    fqtn3 = FullyQualifiedToolName("Tool2", "Toolkit1", "1.0")
    assert fqtn1 == fqtn2
    assert fqtn1 != fqtn3


def test_equality_ignoring_version():
    fqtn1 = FullyQualifiedToolName("Tool1", "Toolkit1", "1.0")
    fqtn2 = FullyQualifiedToolName("Tool1", "Toolkit1", "2.0")
    assert fqtn1.equals_ignoring_version(fqtn2)


def test_ftqn_case_insensitivity():
    fqtn1 = FullyQualifiedToolName("Tool1", "Toolkit1", "latest")
    fqtn2 = FullyQualifiedToolName("TOOL1", "toolKit1", "LATEST")
    assert fqtn1 == fqtn2


def test_hash():
    fqtn1 = FullyQualifiedToolName("Tool1", "Toolkit1", "1.0")
    fqtn2 = FullyQualifiedToolName("TOOL1", "toolkit1", "1.0")
    fqtn3 = FullyQualifiedToolName("Tool2", "Toolkit1", "1.0")
    fqtn_set = {fqtn1, fqtn2, fqtn3}
    assert len(fqtn_set) == 2


def test_from_toolkit():
    toolkit = ToolkitDefinition(name="toolkit1", version="1.0")
    fqtn = FullyQualifiedToolName.from_toolkit("Tool1", toolkit)
    assert fqtn.name == "Tool1"
    assert fqtn.toolkit_name == "toolkit1"
    assert fqtn.toolkit_version == "1.0"
