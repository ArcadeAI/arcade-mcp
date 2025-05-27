import io
import queue

from arcade_serve.mcp.stdio import stdio_reader, stdio_writer


def test_stdio_reader_puts_lines_and_none():
    q: queue.Queue[str | None] = queue.Queue()
    test_input = io.StringIO("line1\nline2\n")

    stdio_reader(test_input, q)

    # We should get the two lines followed by None sentinel
    assert q.get_nowait() == "line1\n"
    assert q.get_nowait() == "line2\n"
    assert q.get_nowait() is None


def test_stdio_writer_reads_until_none():
    q: queue.Queue[str | None] = queue.Queue()
    output_stream = io.StringIO()

    # preload queue with two messages and sentinel
    q.put("msg1")
    q.put("msg2\n")
    q.put(None)

    stdio_writer(output_stream, q)

    # Ensure writer appended newlines when missing
    output_stream.seek(0)
    assert output_stream.read() == "msg1\nmsg2\n"
