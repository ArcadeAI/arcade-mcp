import pytest

from arcade_google.models import CellData, CellExtendedValue, RowData, SheetDataInput
from arcade_google.utils import (
    col_to_index,
    compute_sheet_data_dimensions,
    create_cell_data,
    create_row_data,
    create_sheet_data,
    create_sheet_properties,
    group_contiguous_rows,
    index_to_col,
    is_col_greater,
)


@pytest.fixture
def sheet_data_input_fixture():
    data = {
        1: {
            "A": "name",
            "B": "age",
            "C": "email",
            "D": "score",
            "E": "gender",
            "F": "city",
            "G": "country",
            "H": "registration_date",
        },
        2: {
            "A": "John Doe",
            "B": 28,
            "C": "johndoe@example.com",
            "D": 85.4,
            "E": "Male",
            "F": "New York",
            "G": "USA",
            "H": "2023-01-15",
        },
        10: {
            "A": "Nate Green",
            "B": 30,
            "C": "nateg@example.com",
            "D": 88,
            "E": "Male",
            "F": "Orlando",
            "G": "USA",
            "H": "2024-02-01",
        },
        43: {
            "A": 100,
            "B": 300,
            "H": 123,
            "I": "=SUM(SEQUENCE(10))",
        },
        44: {
            "A": 456,
            "B": 234,
            "H": 123,
            "I": "=SUM(SEQUENCE(10))",
        },
    }
    return SheetDataInput(data=data)


@pytest.mark.parametrize(
    "col, expected_index",
    [
        ("A", 0),
        ("B", 1),
        ("Z", 25),
        ("AA", 26 + 0),
        ("AZ", (1 * 26) + 25),
        ("BA", (2 * 26) + 0),
        ("ZZ", (26 * 26) + 25),
        ("AAA", (1 * 26 * 26) + (1 * 26) + 0),
        ("AAB", (1 * 26 * 26) + (1 * 26) + 1),
        ("QED", (17 * 26 * 26) + (5 * 26) + 3),
    ],
)
def test_col_to_index(col, expected_index):
    assert col_to_index(col) == expected_index


@pytest.mark.parametrize(
    "index, expected_col",
    [
        (0, "A"),
        (1, "B"),
        (25, "Z"),
        (26 + 0, "AA"),
        ((1 * 26) + 25, "AZ"),
        ((2 * 26) + 0, "BA"),
        ((26 * 26) + 25, "ZZ"),
        ((1 * 26 * 26) + (1 * 26) + 0, "AAA"),
        ((1 * 26 * 26) + (1 * 26) + 1, "AAB"),
        ((17 * 26 * 26) + (5 * 26) + 3, "QED"),
    ],
)
def test_index_to_col(index, expected_col):
    assert index_to_col(index) == expected_col


@pytest.mark.parametrize(
    "col1, col2, expected_result",
    [
        ("A", "B", False),
        ("B", "A", True),
        ("AA", "AB", False),
        ("AB", "AA", True),
        ("A", "AA", False),
        ("AA", "A", True),
        ("Z", "AA", False),
        ("AA", "Z", True),
        ("AAA", "AAB", False),
        ("AAB", "AAA", True),
        ("QED", "QEE", False),
        ("QEE", "QED", True),
    ],
)
def test_is_col_greater(col1, col2, expected_result):
    assert is_col_greater(col1, col2) == expected_result


def test_compute_sheet_data_dimensions(sheet_data_input_fixture):
    (min_row, max_row), (min_col_index, max_col_index) = compute_sheet_data_dimensions(
        sheet_data_input_fixture
    )

    expected_min_row = 1
    expected_max_row = 44
    expected_min_col_index = 0  # Column "A"
    expected_max_col_index = 8  # Column "I"

    assert min_row == expected_min_row
    assert max_row == expected_max_row
    assert min_col_index == expected_min_col_index
    assert max_col_index == expected_max_col_index


def test_create_sheet_properties():
    sheet_properties = create_sheet_properties(
        sheet_id=1,
        title="Sheet1",
        row_count=10000,
        column_count=260,
    )

    assert sheet_properties.sheetId == 1
    assert sheet_properties.title == "Sheet1"
    assert sheet_properties.gridProperties.rowCount == 10000
    assert sheet_properties.gridProperties.columnCount == 260


@pytest.mark.parametrize(
    "row_numbers, expected_groups",
    [
        ([], []),
        ([5, 6, 7], [[5, 6, 7]]),
        (
            [1, 2, 3, 5, 6, 7, 8, 9, 10, 11, 18, 19, 20],
            [[1, 2, 3], [5, 6, 7, 8, 9, 10, 11], [18, 19, 20]],
        ),
    ],
)
def test_group_contiguous_rows(row_numbers, expected_groups):
    grouped_rows = group_contiguous_rows(row_numbers)
    assert grouped_rows == expected_groups


@pytest.mark.parametrize(
    "cell_value, expected_cell_data",
    [
        (1, CellExtendedValue(numberValue=1)),
        (1.567, CellExtendedValue(numberValue=1.567)),
        ("test", CellExtendedValue(stringValue="test")),
        (True, CellExtendedValue(boolValue=True)),
        (False, CellExtendedValue(boolValue=False)),
        ("=SUM(A1:B1)", CellExtendedValue(formulaValue="=SUM(A1:B1)")),
    ],
)
def test_create_cell_data(cell_value, expected_cell_data):
    cell_data = create_cell_data(cell_value)
    assert cell_data.userEnteredValue == expected_cell_data


def test_create_row_data():
    row_data = {
        "A": 1,  # Column index 0
        "B": 2.5,  # Column index 1
        "AA": "test",  # Column index 26
        "BA": True,  # Column index 52
        "BB": "=SUM(A1:B1)",  # Column index 53
    }
    min_col_index = 0  # Column "A"
    max_col_index = 53  # Column "BB"

    expected_row_data = RowData(
        values=[
            CellData(userEnteredValue=CellExtendedValue(stringValue=""))
            for _ in range(max_col_index + 1)
        ]
    )
    expected_row_data.values[0].userEnteredValue = CellExtendedValue(numberValue=1)
    expected_row_data.values[1].userEnteredValue = CellExtendedValue(numberValue=2.5)
    expected_row_data.values[26].userEnteredValue = CellExtendedValue(stringValue="test")
    expected_row_data.values[52].userEnteredValue = CellExtendedValue(boolValue=True)
    expected_row_data.values[53].userEnteredValue = CellExtendedValue(formulaValue="=SUM(A1:B1)")

    row_data = create_row_data(row_data, min_col_index, max_col_index)

    assert len(row_data.values) == len(expected_row_data.values)
    for cell, expected in zip(row_data.values, expected_row_data.values):
        assert cell.userEnteredValue == expected.userEnteredValue


def test_create_sheet_data():
    from arcade_google.models import CellData, CellExtendedValue, SheetDataInput
    from arcade_google.utils import create_cell_data

    test_data = {
        2: {"B": "row2B", "C": 200},
        3: {"B": "row3B"},
        5: {"A": "=SUM(A1:A1)", "C": "row5C"},
    }
    sheet_data_input = SheetDataInput(data=test_data)
    min_col_index = 0  # Column "A"
    max_col_index = 2  # Column "C"

    grid_data_list = create_sheet_data(sheet_data_input, min_col_index, max_col_index)

    assert len(grid_data_list) == 2, "Should have two groups of contiguous rows"

    group1 = grid_data_list[0]
    assert group1.startRow == 1
    assert group1.startColumn == min_col_index
    assert len(group1.rowData) == 2

    row2_cells = group1.rowData[0].values
    expected_row2 = [
        CellData(userEnteredValue=CellExtendedValue(stringValue="")),
        create_cell_data("row2B"),
        create_cell_data(200),
    ]
    for cell, expected in zip(row2_cells, expected_row2):
        assert cell.userEnteredValue == expected.userEnteredValue

    row3_cells = group1.rowData[1].values
    expected_row3 = [
        CellData(userEnteredValue=CellExtendedValue(stringValue="")),
        create_cell_data("row3B"),
        CellData(userEnteredValue=CellExtendedValue(stringValue="")),
    ]
    for cell, expected in zip(row3_cells, expected_row3):
        assert cell.userEnteredValue == expected.userEnteredValue

    group2 = grid_data_list[1]
    assert group2.startRow == 4
    assert group2.startColumn == min_col_index
    assert len(group2.rowData) == 1

    row5_cells = group2.rowData[0].values
    expected_row5 = [
        create_cell_data("=SUM(A1:A1)"),
        CellData(userEnteredValue=CellExtendedValue(stringValue="")),
        create_cell_data("row5C"),
    ]
    for cell, expected in zip(row5_cells, expected_row5):
        assert cell.userEnteredValue == expected.userEnteredValue
