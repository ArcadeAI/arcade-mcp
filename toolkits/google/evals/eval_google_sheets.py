from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    SimilarityCritic,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_google
from arcade_google.tools import (
    create_spreadsheet,
    get_spreadsheet,
)

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.9,
    warn_threshold=0.95,
)

catalog = ToolCatalog()
catalog.add_module(arcade_google)

sheet_content_prompt = """name age email score gender city country registration_date
John Doe 28 johndoe@example.com 85 Male New York USA 2023-01-15
Jane Smith 34 janesmith@example.com 92 Female Los Angeles USA 2023-02-20
Alice Johnson 22 alicej@example.com 78 Female Chicago USA 2023-03-10
Bob Brown 45 bobbrown@example.com 88 Male Houston USA 2023-04-05
Charlie Davis 30 charlied@example.com 95 Male Phoenix USA 2023-05-12
Eve White 27 evewhite@example.com 82 Female Philadelphia USA 2023-06-18
Frank Black 40 frankb@example.com 90 Male San Antonio USA 2023-07-25
Grace Green 29 graceg@example.com 76 Female Dallas USA 2023-08-30
Hank Blue 35 hankb@example.com 89 Male San Diego USA 2023-09-15
Ivy Red 31 ivyred@example.com 91 Female San Jose USA 2023-10-01
Michael Grey 33 michaelg@example.com 87 Male Seattle USA 2023-10-05
Nina Black 26 ninab@example.com 84 Female Miami USA 2023-10-10
Oscar White 38 oscarw@example.com 90 Male Atlanta USA 2023-10-15
Paula Green 32 paulag@example.com 93 Female Boston USA 2023-10-20
Quentin Brown 29 quentinb@example.com 81 Male Denver USA 2023-10-25
Rachel Blue 24 rachelb@example.com 79 Female Orlando USA 2023-10-30
Steve Red 36 stever@example.com 88 Male Las Vegas USA 2023-11-01
Tina Yellow 30 tinay@example.com 85 Female Portland USA 2023-11-05
Ursula Pink 27 ursulap@example.com 82 Female San Francisco USA 2023-11-10
Victor Grey 41 victorg@example.com 91 Male Charlotte USA 2023-11-15
Wendy Black 34 wendyb@example.com 89 Female Detroit USA 2023-11-20
Xander White 29 xanderw@example.com 86 Male Indianapolis USA 2023-11-25
Yvonne Green 25 yvonnag@example.com 83 Female Columbus USA 2023-11-30
Zachary Blue 37 zacharyb@example.com 90 Male Jacksonville USA 2023-12-01
Alice Brown 28 aliceb@example.com 80 Female Memphis USA 2023-12-05
Brian Black 39 brianb@example.com 92 Male Nashville USA 2023-12-10
Cathy Green 31 cathyg@example.com 84 Female Virginia Beach USA 2023-12-15
Daniel White 30 danielw@example.com 88 Male Atlanta USA 2023-12-20
Eva Red 26 evar@example.com 81 Female New Orleans USA 2023-12-25
Frankie Grey 35 frankieg@example.com 90 Male San Antonio USA 2023-12-30
Gina Blue 29 ginab@example.com 87 Female San Diego USA 2024-01-01
Henry Black 42 henryb@example.com 93 Male Philadelphia USA 2024-01-05
Isla Green 24 islag@example.com 79 Female Chicago USA 2024-01-10
Jack White 33 jackw@example.com 85 Male Los Angeles USA 2024-01-15
Kathy Red 31 kathyr@example.com 82 Female Miami USA 2024-01-20
Liam Grey 36 liamg@example.com 89 Male Seattle USA 2024-01-25
Mia Black 27 miab@example.com 80 Female Denver USA 2024-01-30
Nate Green 30 nateg@example.com 88 Male Orlando USA 2024-02-01
- (empty row)
- (empty row)
- (empty row)
100, 300, 234, 399, 5039, 2345, 23526, 123, 54, 234, 54, 23, 12, 57, 1324, (the formula for sum of everything to the left)
- (empty row)
- (empty row)
- (empty row)
- (empty row)
- (empty row)
- (empty row)
- (empty row)
- (empty row)
- (empty row)
- (empty row)
- (empty row)
- (empty row)
- (empty row)
- (empty row)
- (empty row)
- (empty row)
456, 234, 234, 399, 234, 1234, 23526, 123, 54, 234, 4567, 23, 12, 234, 1324, (the formula for sum of everything to the left)
"""


@tool_eval()
def create_spreadsheet_eval() -> EvalSuite:
    """Create an evaluation suite for Google Sheets create_spreadsheet tool."""

    sheet_content_expected1 = """{"1": {"A": "name", "B": "age", "C": "email", "D": "score", "E": "gender", "F": "city", "G": "country", "H": "registration_date"}, "2": {"A": "John Doe", "B": 28, "C": "johndoe@example.com", "D": 85, "E": "Male", "F": "New York", "G": "USA", "H": "2023-01-15"}, "3": {"A": "Jane Smith", "B": 34, "C": "janesmith@example.com", "D": 92, "E": "Female", "F": "Los Angeles", "G": "USA", "H": "2023-02-20"}, "4": {"A": "Alice Johnson", "B": 22, "C": "alicej@example.com", "D": 78, "E": "Female", "F": "Chicago", "G": "USA", "H": "2023-03-10"}, "5": {"A": "Bob Brown", "B": 45, "C": "bobbrown@example.com", "D": 88, "E": "Male", "F": "Houston", "G": "USA", "H": "2023-04-05"}, "6": {"A": "Charlie Davis", "B": 30, "C": "charlied@example.com", "D": 95, "E": "Male", "F": "Phoenix", "G": "USA", "H": "2023-05-12"}, "7": {"A": "Eve White", "B": 27, "C": "evewhite@example.com", "D": 82, "E": "Female", "F": "Philadelphia", "G": "USA", "H": "2023-06-18"}, "8": {"A": "Frank Black", "B": 40, "C": "frankb@example.com", "D": 90, "E": "Male", "F": "San Antonio", "G": "USA", "H": "2023-07-25"}, "9": {"A": "Grace Green", "B": 29, "C": "graceg@example.com", "D": 76, "E": "Female", "F": "Dallas", "G": "USA", "H": "2023-08-30"}, "10": {"A": "Hank Blue", "B": 35, "C": "hankb@example.com", "D": 89, "E": "Male", "F": "San Diego", "G": "USA", "H": "2023-09-15"}, "11": {"A": "Ivy Red", "B": 31, "C": "ivyred@example.com", "D": 91, "E": "Female", "F": "San Jose", "G": "USA", "H": "2023-10-01"}, "12": {"A": "Michael Grey", "B": 33, "C": "michaelg@example.com", "D": 87, "E": "Male", "F": "Seattle", "G": "USA", "H": "2023-10-05"}, "13": {"A": "Nina Black", "B": 26, "C": "ninab@example.com", "D": 84, "E": "Female", "F": "Miami", "G": "USA", "H": "2023-10-10"}, "14": {"A": "Oscar White", "B": 38, "C": "oscarw@example.com", "D": 90, "E": "Male", "F": "Atlanta", "G": "USA", "H": "2023-10-15"}, "15": {"A": "Paula Green", "B": 32, "C": "paulag@example.com", "D": 93, "E": "Female", "F": "Boston", "G": "USA", "H": "2023-10-20"}, "16": {"A": "Quentin Brown", "B": 29, "C": "quentinb@example.com", "D": 81, "E": "Male", "F": "Denver", "G": "USA", "H": "2023-10-25"}, "17": {"A": "Rachel Blue", "B": 24, "C": "rachelb@example.com", "D": 79, "E": "Female", "F": "Orlando", "G": "USA", "H": "2023-10-30"}, "18": {"A": "Steve Red", "B": 36, "C": "stever@example.com", "D": 88, "E": "Male", "F": "Las Vegas", "G": "USA", "H": "2023-11-01"}, "19": {"A": "Tina Yellow", "B": 30, "C": "tinay@example.com", "D": 85, "E": "Female", "F": "Portland", "G": "USA", "H": "2023-11-05"}, "20": {"A": "Ursula Pink", "B": 27, "C": "ursulap@example.com", "D": 82, "E": "Female", "F": "San Francisco", "G": "USA", "H": "2023-11-10"}, "21": {"A": "Victor Grey", "B": 41, "C": "victorg@example.com", "D": 91, "E": "Male", "F": "Charlotte", "G": "USA", "H": "2023-11-15"}, "22": {"A": "Wendy Black", "B": 34, "C": "wendyb@example.com", "D": 89, "E": "Female", "F": "Detroit", "G": "USA", "H": "2023-11-20"}, "23": {"A": "Xander White", "B": 29, "C": "xanderw@example.com", "D": 86, "E": "Male", "F": "Indianapolis", "G": "USA", "H": "2023-11-25"}, "24": {"A": "Yvonne Green", "B": 25, "C": "yvonnag@example.com", "D": 83, "E": "Female", "F": "Columbus", "G": "USA", "H": "2023-11-30"}, "25": {"A": "Zachary Blue", "B": 37, "C": "zacharyb@example.com", "D": 90, "E": "Male", "F": "Jacksonville", "G": "USA", "H": "2023-12-01"}, "26": {"A": "Alice Brown", "B": 28, "C": "aliceb@example.com", "D": 80, "E": "Female", "F": "Memphis", "G": "USA", "H": "2023-12-05"}, "27": {"A": "Brian Black", "B": 39, "C": "brianb@example.com", "D": 92, "E": "Male", "F": "Nashville", "G": "USA", "H": "2023-12-10"}, "28": {"A": "Cathy Green", "B": 31, "C": "cathyg@example.com", "D": 84, "E": "Female", "F": "Virginia Beach", "G": "USA", "H": "2023-12-15"}, "29": {"A": "Daniel White", "B": 30, "C": "danielw@example.com", "D": 88, "E": "Male", "F": "Atlanta", "G": "USA", "H": "2023-12-20"}, "30": {"A": "Eva Red", "B": 26, "C": "evar@example.com", "D": 81, "E": "Female", "F": "New Orleans", "G": "USA", "H": "2023-12-25"}, "31": {"A": "Frankie Grey", "B": 35, "C": "frankieg@example.com", "D": 90, "E": "Male", "F": "San Antonio", "G": "USA", "H": "2023-12-30"}, "32": {"A": "Gina Blue", "B": 29, "C": "ginab@example.com", "D": 87, "E": "Female", "F": "San Diego", "G": "USA", "H": "2024-01-01"}, "33": {"A": "Henry Black", "B": 42, "C": "henryb@example.com", "D": 93, "E": "Male", "F": "Philadelphia", "G": "USA", "H": "2024-01-05"}, "34": {"A": "Isla Green", "B": 24, "C": "islag@example.com", "D": 79, "E": "Female", "F": "Chicago", "G": "USA", "H": "2024-01-10"}, "35": {"A": "Jack White", "B": 33, "C": "jackw@example.com", "D": 85, "E": "Male", "F": "Los Angeles", "G": "USA", "H": "2024-01-15"}, "36": {"A": "Kathy Red", "B": 31, "C": "kathyr@example.com", "D": 82, "E": "Female", "F": "Miami", "G": "USA", "H": "2024-01-20"}, "37": {"A": "Liam Grey", "B": 36, "C": "liamg@example.com", "D": 89, "E": "Male", "F": "Seattle", "G": "USA", "H": "2024-01-25"}, "38": {"A": "Mia Black", "B": 27, "C": "miab@example.com", "D": 80, "E": "Female", "F": "Denver", "G": "USA", "H": "2024-01-30"}, "39": {"A": "Nate Green", "B": 30, "C": "nateg@example.com", "D": 88, "E": "Male", "F": "Orlando", "G": "USA", "H": "2024-02-01"}, "40": {}, "41": {}, "42": {}, "43": {"A": 100, "B": 300, "C": 234, "D": 399, "E": 5039, "F": 2345, "G": 23526, "H": 123, "I": 54, "J": 234, "K": 54, "L": 23, "M": 12, "N": 57, "O": 1324, "P": "(the formula for sum of everything to the left)"}, "44": {}, "45": {}, "46": {}, "47": {}, "48": {}, "49": {}, "50": {}, "51": {}, "52": {}, "53": {}, "54": {}, "55": {}, "56": {}, "57": {}, "58": {}, "59": {}, "60": {"A": 456, "B": 234, "C": 234, "D": 399, "E": 234, "F": 1234, "G": 23526, "H": 123, "I": 54, "J": 234, "K": 4567, "L": 899, "M": 12, "N": 234, "O": 45, "P": "(the formula for sum of everything to the left)"}}"""
    sheet_content_sparse_expected = """{"1": {"AA": "=SUM(A1,A2,A3)", "3782": {"A": 3783, "D": 3784, "AAZ": 3785, "ZZFS": 3786, "CA": 3787}}}"""

    suite = EvalSuite(
        name="Google Sheets Tools Evaluation",
        system_message="You are an AI assistant that can manage Google Sheets using the provided tools.",
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Create a spreadsheet from large data payload",
        user_message=f"Create a spreadsheet named 'Data' with the following content:\n{sheet_content_prompt}",
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_spreadsheet,
                args={
                    "title": "Data",
                    "data": sheet_content_expected1,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="title", weight=0.1),
            SimilarityCritic(critic_field="data", weight=0.9, similarity_threshold=0.99),
        ],
    )

    suite.add_case(
        name="Create a spreadsheet from sparse data payload",
        user_message="Create a spreadsheet named 'Sparse Data' that fills the 27th column in the first row with the formula that sums A1, A2, and A3 cells. The 3782nd row should have its A, D, AAZ, ZZFS, and CA columns filled with the numbers 1, 2, 3, 4, and 5, respectively, summed with its row number.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_spreadsheet,
                args={
                    "title": "Sparse Data",
                    "data": sheet_content_sparse_expected,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="title", weight=0.1),
            SimilarityCritic(critic_field="data", weight=0.9, similarity_threshold=0.95),
        ],
    )

    return suite


@tool_eval()
def get_spreadsheet_eval() -> EvalSuite:
    """Create an evaluation suite for Google Sheets get_spreadsheet tool."""

    suite = EvalSuite(
        name="Google Sheets Tools Evaluation",
        system_message="You are an AI assistant that can manage Google Sheets using the provided tools.",
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Get a spreadsheet",
        user_message="Get the data in the second sheet of the spreadsheet with the following id 1L2ovCUcRNOacoWxtLV3jgaidWZq4Bw_WXbIWJcxobN0",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_spreadsheet,
                args={
                    "spreadsheet_id": "1L2ovCUcRNOacoWxtLV3jgaidWZq4Bw_WXbIWJcxobN0",
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="spreadsheet_id", weight=1.0),
        ],
    )

    return suite
