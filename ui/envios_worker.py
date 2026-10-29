"""Workers de planejamento e envio executados fora da thread da GUI.

Ler a planilha de contatos, varrer a pasta e enviar pelo Outlook são
operações bloqueantes. Elas rodam em ``QThread`` e conversam com a interface
somente por sinais Qt.

.. note::
   Este módulo é **somente funcional** e não faz parte do redesign visual.
   ``PlanWorker`` e ``SendWorker`` são referenciados por
   ``ui/envios_tab.py``; preserve os construtores e os sinais.
"""

from __future__ import annotations

import threading
import traceback
from pathlib import Path
from typing import Iterable, Sequence

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from backend.envios import (
    EnvioError,
    EnvioResultado,
    PlanoEnvios,
    enviar_plano,
    montar_plano,
)

__all__ = ["PlanWorker", "SendWorker"]


class PlanWorker(QObject):
    """Monta o plano de envios (contatos + arquivos) sem abrir o Outlook."""

    log = pyqtSignal(str, str)
    finished = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(
        self,
        report_key: str,
        contatos_path: str | Path,
        pasta_arquivos: str | Path,
        copia_manual: Sequence[str] | None = None,
        assunto: str | None = None,
        corpo: str | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._report_key = report_key
        self._contatos_path = contatos_path
        self._pasta_arquivos = pasta_arquivos
        self._copia_manual = list(copia_manual or [])
        self._assunto = assunto
        self._corpo = corpo

    @pyqtSlot()
    def run(self) -> None:
        """Executa :func:`backend.envios.montar_plano` na thread de trabalho."""
        try:
            self.log.emit(
                "Lendo a planilha de contatos e a pasta de arquivos INS…",
                "info",
            )
            plano: PlanoEnvios = montar_plano(
                self._report_key,
                self._contatos_path,
                self._pasta_arquivos,
                copia_manual=self._copia_manual,
                assunto=self._assunto,
                corpo=self._corpo,
            )
        except EnvioError as erro:
            self.failed.emit(str(erro))
        except Exception as erro:  # noqa: BLE001 - rede de segurança
            detalhe = "".join(
                traceback.format_exception_only(type(erro), erro)
            ).strip()
            self.failed.emit(
                "Ocorreu um erro inesperado ao preparar os envios.\n\n"
                f"Detalhe técnico: {detalhe or erro}"
            )
        else:
            self.finished.emit(plano)


class SendWorker(QObject):
    """Envia os grupos selecionados pelo Outlook Desktop."""

    progress = pyqtSignal(int, int, str)
    log = pyqtSignal(str, str)
    finished = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(
        self,
        plano: PlanoEnvios,
        chaves: Iterable[str],
        cancel_flag: threading.Event | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._plano = plano
        self._chaves = list(chaves)
        self._cancel_flag = cancel_flag or threading.Event()

    @pyqtSlot()
    def run(self) -> None:
        """Executa :func:`backend.envios.enviar_plano` na thread de trabalho."""
        try:
            resultado: EnvioResultado = enviar_plano(
                self._plano,
                self._chaves,
                on_progress=self.progress.emit,
                on_log=self.log.emit,
                should_cancel=self._cancel_flag.is_set,
            )
        except EnvioError as erro:
            self.failed.emit(str(erro))
        except Exception as erro:  # noqa: BLE001 - rede de segurança
            detalhe = "".join(
                traceback.format_exception_only(type(erro), erro)
            ).strip()
            self.failed.emit(
                "Ocorreu um erro inesperado durante o envio.\n\n"
                f"Detalhe técnico: {detalhe or erro}"
            )
        else:
            self.finished.emit(resultado)
