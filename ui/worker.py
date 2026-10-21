"""Execução do backend fora da thread da interface gráfica.

O :class:`~backend.processor.DashboardProcessor` usa automação do Excel
(xlwings/COM) e portanto é **bloqueante**.  O :class:`JobWorker` executa o
``run()`` dentro de uma ``QThread`` e repassa o andamento para a interface
apenas por meio de sinais Qt.
"""

from __future__ import annotations

import threading
import traceback

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from backend import (
    DashboardProcessor,
    JobCancelled,
    JobConfig,
    JobError,
    JobResult,
)

__all__ = ["JobWorker"]


class JobWorker(QObject):
    """Worker que roda :meth:`DashboardProcessor.run` em thread separada.

    Sinais:

    * ``progress(atual, total, grupo)`` -- avanço da geração;
    * ``log(mensagem, nivel)`` -- mensagens coloridas do log;
    * ``finished(resultado)`` -- conclusão com sucesso;
    * ``failed(mensagem)`` -- erro com texto amigável para o usuário;
    * ``cancelled()`` -- cancelamento pedido pelo usuário.
    """

    progress = pyqtSignal(int, int, str)
    log = pyqtSignal(str, str)
    finished = pyqtSignal(object)
    failed = pyqtSignal(str)
    cancelled = pyqtSignal()

    def __init__(
        self,
        cancel_flag: threading.Event | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._cancel_flag = cancel_flag or threading.Event()
        self._config: JobConfig | None = None

    # ------------------------------------------------------------------
    # API
    # ------------------------------------------------------------------
    def set_config(self, config: JobConfig) -> None:
        """Guarda a configuração que será processada em :meth:`run`."""
        self._config = config

    def request_cancel(self) -> None:
        """Sinaliza que o usuário pediu o cancelamento da execução."""
        self._cancel_flag.set()

    @property
    def cancel_requested(self) -> bool:
        """Informa se o cancelamento foi solicitado."""
        return self._cancel_flag.is_set()

    @pyqtSlot()
    def run(self) -> None:
        """Executa o processamento do backend (chamado dentro da QThread)."""
        config = self._config
        if config is None:
            self.failed.emit(
                "Nenhuma configuração foi informada para a geração."
            )
            return

        processor = DashboardProcessor(
            on_progress=self._emit_progress,
            on_log=self._emit_log,
            should_cancel=self._cancel_flag.is_set,
        )

        try:
            resultado: JobResult = processor.run(config)
        except JobCancelled:
            self.cancelled.emit()
        except JobError as erro:
            self.failed.emit(str(erro))
        except Exception as erro:  # noqa: BLE001 - rede de segurança
            detalhe = traceback.format_exception_only(type(erro), erro)
            resumo = "".join(detalhe).strip() or str(erro)
            self.failed.emit(
                "Ocorreu um erro inesperado durante a geração dos "
                "dashboards.\n\n"
                f"Detalhe técnico: {resumo}"
            )
        else:
            self.finished.emit(resultado)

    # ------------------------------------------------------------------
    # Callbacks do backend
    # ------------------------------------------------------------------
    @pyqtSlot(int, int, str)
    def _emit_progress(self, atual: int, total: int, grupo: str) -> None:
        """Repassa o progresso do backend para a interface."""
        self.progress.emit(int(atual), int(total), str(grupo))

    @pyqtSlot(str, str)
    def _emit_log(self, mensagem: str, nivel: str) -> None:
        """Repassa uma mensagem de log do backend para a interface."""
        self.log.emit(str(mensagem), str(nivel))
