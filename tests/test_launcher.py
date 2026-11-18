import errno
import sys
from unittest.mock import Mock
import run


def test_open_launcher_does_not_open_an_occupied_old_port(monkeypatch):
    import backend.api.server as server

    fake = Mock(side_effect=[OSError(errno.EADDRINUSE, "occupied"), None])
    monkeypatch.setattr(server, "run_server", fake)
    monkeypatch.setattr(sys, "argv", ["run.py", "--open", "--port", "9870"])
    run.main()
    assert [call.args[0] for call in fake.call_args_list] == [9870, 9871]
    assert fake.call_args_list[-1].kwargs["on_ready"] is run.open_browser
