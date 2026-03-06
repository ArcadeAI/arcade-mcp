from pathlib import Path

from arcade_cli.utils import get_eval_files


def test_get_eval_files_with_spaces(tmp_path: Path) -> None:
    eval_root = tmp_path / "eval dir with spaces"
    eval_root.mkdir()

    file_one = eval_root / "eval_one.py"
    file_one.write_text("print('one')\n", encoding="utf-8")

    nested = eval_root / "nested dir"
    nested.mkdir()
    file_two = nested / "eval_two.py"
    file_two.write_text("print('two')\n", encoding="utf-8")

    results = get_eval_files(str(eval_root))
    resolved = {p.resolve() for p in results}

    assert file_one.resolve() in resolved
    assert file_two.resolve() in resolved
