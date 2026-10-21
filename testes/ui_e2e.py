"""Teste de integração da interface (requer Excel).

Abre a ``MainWindow`` em modo offscreen, preenche os caminhos com planilhas
sintéticas, clica em "Gerar dashboards" e verifica se os arquivos foram
gravados na pasta de saída escolhida.

Execução (a partir de ins_dashboard_app)::

    python -m testes.ui_e2e
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtGui import QFont  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

from testes.smoke_test import _build_fixtures  # noqa: E402
from ui import main_window as main_window_module  # noqa: E402
from ui.main_window import MainWindow  # noqa: E402
from ui.theme import APP_FONT, build_stylesheet  # noqa: E402


class _FakeSettings:
    """QSettings em memória para não poluir o registro do Windows."""

    _store: dict[tuple[str, str], dict[str, object]] = {}

    def __init__(self, organization: str, application: str) -> None:
        self._data = self._store.setdefault((organization, application), {})

    def value(self, key: str, default: object = None) -> object:
        return self._data.get(key, default)

    def setValue(self, key: str, value: object) -> None:
        self._data[key] = value


def main() -> int:
    main_window_module.QSettings = _FakeSettings  # type: ignore[assignment]

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        (
            source,
            template,
            _transportador_source,
            _transportador_template,
        ) = _build_fixtures(base)
        output = base / "dashboards"
        output.mkdir()

        app = QApplication([])
        app.setStyle("Fusion")
        app.setFont(QFont(APP_FONT, 9))
        app.setStyleSheet(build_stylesheet())

        window = MainWindow()
        window.show()
        app.processEvents()

        window._segmented.set_current("motorista")
        window._source_selector.set_path(source)
        window._template_selector.set_path(template)
        window._output_selector.set_path(output)

        window._generate_button.click()
        app.processEvents()

        deadline = time.monotonic() + 180
        while window._running and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.05)
        app.processEvents()

        if window._running:
            print("FALHOU: a geração não terminou no tempo esperado.")
            return 1

        produced = sorted(path.name for path in output.glob("*.xlsx"))
        print("status:", window._status_label.text())
        print("resumo:", window._summary_label.text())
        print("led:", window._led.state)
        print("arquivos:", produced)

        assert window._led.state == "ok", window._led.state
        assert len(produced) == 2, produced
        assert all(name.startswith("INS do Motorista - ") for name in produced)
        assert window._open_folder_button.isEnabled()

        window.close()
        app.processEvents()
        print("OK: interface gerou os dashboards pela QThread.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
