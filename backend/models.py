"""Modelos de dados compartilhados entre backend e interface gráfica."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .reports import ReportType


class JobError(Exception):
    """Erro esperado de configuração ou de execução, com mensagem amigável."""


class JobCancelled(Exception):
    """Sinaliza que o usuário cancelou a geração dos dashboards."""


@dataclass(frozen=True, slots=True)
class JobConfig:
    """Entradas escolhidas pelo usuário na interface."""

    report_type: ReportType
    source_file: Path
    template_file: Path
    output_dir: Path

    def validate(self) -> None:
        """Valida os caminhos escolhidos.

        Levanta :class:`JobError` com uma mensagem pronta para exibição.
        """
        problems: list[str] = []

        if not self.source_file:
            problems.append("Selecione o arquivo do relatório (.xlsx).")
        elif not self.source_file.is_file():
            problems.append(
                f"Arquivo do relatório não encontrado:\n{self.source_file}"
            )
        elif self.source_file.suffix.lower() not in {".xlsx", ".xlsm"}:
            problems.append(
                "O arquivo do relatório precisa ser .xlsx ou .xlsm "
                f"(recebido: {self.source_file.suffix or 'sem extensão'})."
            )

        if not self.template_file:
            problems.append("Selecione o template do dashboard (.xlsx).")
        elif not self.template_file.is_file():
            problems.append(
                f"Template do dashboard não encontrado:\n{self.template_file}"
            )
        elif self.template_file.suffix.lower() not in {".xlsx", ".xlsm", ".xltx", ".xltm"}:
            problems.append(
                "O template precisa ser .xlsx, .xlsm, .xltx ou .xltm "
                f"(recebido: {self.template_file.suffix or 'sem extensão'})."
            )

        if not self.output_dir:
            problems.append("Selecione a pasta onde os dashboards serão salvos.")
        elif self.output_dir.exists() and not self.output_dir.is_dir():
            problems.append(
                f"O destino dos dashboards não é uma pasta:\n{self.output_dir}"
            )

        if problems:
            raise JobError("\n\n".join(problems))


@dataclass(frozen=True, slots=True)
class GroupInfo:
    """Um grupo (motorista/transportadora) encontrado na planilha."""

    name: str
    rows: int
    output_name: str


@dataclass(frozen=True, slots=True)
class GroupResult:
    """Resultado da geração de um dashboard."""

    group: str
    rows: int
    output_path: Path


@dataclass(slots=True)
class JobResult:
    """Resumo de uma execução concluída."""

    report_label: str
    outputs: list[GroupResult] = field(default_factory=list)
    total_rows: int = 0
    duration_seconds: float = 0.0
    warnings: list[str] = field(default_factory=list)

    @property
    def dashboard_count(self) -> int:
        return len(self.outputs)
