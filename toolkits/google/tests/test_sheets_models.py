from arcade_google.models import SheetDataInput


def test_sheet_input_data_init():
    data = '{"1":{"A":"name","B":"age","C":"email","D":"score","E":"gender","F":"city","G":"country","H":"registration_date"},"34":{"A":"Isla Green","B":24,"C":"islag@example.com","D":79,"E":"Female","F":"Chicago","G":"USA","H":"2024-01-10"},"38":{"A":"Mia Black","B":27,"C":"miab@example.com","D":80,"E":"Female","F":"Denver","G":"USA","H":"2024-01-30"},"39":{"A":"Nate Green","B":30,"C":"nateg@example.com","D":88,"E":"Male","F":"Orlando","G":"USA","H":"2024-02-01"},"43":{"A":100,"B":300,"C":234,"D":399,"E":5039,"F":2345,"G":23526,"H":123,"I":54,"J":234,"K":54,"L":23,"M":12,"N":57,"O":1324},"47":{"A":456,"B":234,"C":234,"D":399,"E":234,"F":1234,"G":23526,"H":123,"I":54,"J":234,"K":4567,"L":23,"M":12,"N":234,"O":1324}}'
    expected_data = {
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
        34: {
            "A": "Isla Green",
            "B": 24,
            "C": "islag@example.com",
            "D": 79,
            "E": "Female",
            "F": "Chicago",
            "G": "USA",
            "H": "2024-01-10",
        },
        38: {
            "A": "Mia Black",
            "B": 27,
            "C": "miab@example.com",
            "D": 80,
            "E": "Female",
            "F": "Denver",
            "G": "USA",
            "H": "2024-01-30",
        },
        39: {
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
            "C": 234,
            "D": 399,
            "E": 5039,
            "F": 2345,
            "G": 23526,
            "H": 123,
            "I": 54,
            "J": 234,
            "K": 54,
            "L": 23,
            "M": 12,
            "N": 57,
            "O": 1324,
        },
        47: {
            "A": 456,
            "B": 234,
            "C": 234,
            "D": 399,
            "E": 234,
            "F": 1234,
            "G": 23526,
            "H": 123,
            "I": 54,
            "J": 234,
            "K": 4567,
            "L": 23,
            "M": 12,
            "N": 234,
            "O": 1324,
        },
    }

    sheet_input_data = SheetDataInput(data=data)
    assert sheet_input_data.data == expected_data
