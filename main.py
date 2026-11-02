"""Ponto de entrada do INS Dashboard Studio.

Executa a interface gráfica PyQt6 com o visual institucional GrupoSC:

    python ins_dashboard_app/main.py

.. note::
   Este arquivo é **funcional e estável**: define o ``QApplication``, o estilo
   ``Fusion``, a fonte, o ícone e o QSS global. O tema (claro/escuro) é
   restaurado pela ``MainWindow`` a partir de ``QSettings``.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Permite executar ``python ins_dashboard_app/main.py`` a partir de qualquer
# diretório, garantindo a importação de ``ui`` e ``backend``.
_APP_DIR = Path(__file__).resolve().parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

from PyQt6.QtGui import QFont  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

from ui.main_window import MainWindow  # noqa: E402
from ui.theme import APP_FONT, APP_NAME, build_stylesheet  # noqa: E402
from ui.widgets import create_app_icon  # noqa: E402


def build_application(argv: list[str] | None = None) -> QApplication:
    """Cria e configura o ``QApplication`` com estilo, fonte e ícone."""
    app = QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("INS")
    app.setStyle("Fusion")
    app.setFont(QFont(APP_FONT, 9))
    # O QSS carrega as fontes Chivo embarcadas antes de o ícone ser desenhado.
    app.setStyleSheet(build_stylesheet())
    app.setWindowIcon(create_app_icon())
    return app


def main(argv: list[str] | None = None) -> int:
    """Abre a janela principal e executa o laço de eventos."""
    app = build_application(argv)
    window = MainWindow()
    window.showMaximized()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
