from enum import Enum


# Models and enums for the e2b code interpreter
class E2BSupportedLanguage(str, Enum):
    PYTHON = "python"
    JAVASCRIPT = "js"
    R = "r"
    JAVA = "java"
    BASH = "bash"
