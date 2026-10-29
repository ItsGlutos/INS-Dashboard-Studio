"""Motor de geração dos dashboards INS (backend, sem dependência de UI).

O fluxo reproduz fielmente os notebooks originais:

1. lê a aba ``INS`` da planilha de origem;
2. filtra/remove colunas conforme o tipo de relatório;
3. agrupa por motorista (``Apelido``) ou transportadora (``TRANSPORTADOR``);
4. para cada grupo, preenche a tabela do template no Excel, recalcula,
   atualiza as consultas e salva um arquivo novo. Nos relatórios com
   ``ReportType.reuse_template`` (Transportador) o template é aberto uma única
   vez e cada grupo é salvo com ``SaveCopyAs``, mantendo o modelo de dados
   quente entre os grupos.

Todos os caminhos vêm de :class:`~backend.models.JobConfig`; nada é fixo no
código.
"""

from __future__ import annotations

import importlib
import importlib.util
import shutil
import sys
import tempfile
import time
import warnings
from pathlib import Path
from typing import Callable

import pandas as pd

from .models import (
    GroupInfo,
    GroupResult,
    JobCancelled,
    JobConfig,
    JobError,
    JobResult,
)
from .reports import ReportType

ProgressCallback = Callable[[int, int, str], None]
LogCallback = Callable[[str, str], None]
CancelCallback = Callable[[], bool]

# Constantes do Excel (mesmos valores usados nos notebooks).
XL_CALCULATION_MANUAL = -4135
XL_CALCULATION_AUTOMATIC = -4105

# Leitura rápida com python-calamine quando instalado (7x mais rápido que
# openpyxl em planilhas grandes). Sem ele, o pandas usa openpyxl.
_CALAMINE_AVAILABLE = importlib.util.find_spec("python_calamine") is not None

_ICON_OK = "success"
_ICON_INFO = "info"
_ICON_WARNING = "warning"
_ICON_ERROR = "error"


def _noop_progress(current: int, total: int, group: str) -> None:  # pragma: no cover
    pass


def _noop_log(message: str, level: str) -> None:  # pragma: no cover
    pass


def _never_cancel() -> bool:
    return False


class DashboardProcessor:
    """Executa a geração dos dashboards a partir de uma :class:`JobConfig`.

    Os callbacks são opcionais e permitem que a interface acompanhe o
    progresso sem acoplar o backend ao PyQt6::

        processor = DashboardProcessor(
            on_progress=lambda atual, total, grupo: ...,
            on_log=lambda mensagem, nivel: ...,
            should_cancel=lambda: parar.is_set(),
        )
        resultado = processor.run(config)
    """

    def __init__(
        self,
        on_progress: ProgressCallback | None = None,
        on_log: LogCallback | None = None,
        should_cancel: CancelCallback | None = None,
    ) -> None:
        self._progress_cb = on_progress or _noop_progress
        self._log_cb = on_log or _noop_log
        self._cancel_cb = should_cancel or _never_cancel
        self._xlwings = None

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------
    def discover_groups(self, config: JobConfig) -> list[GroupInfo]:
        """Lê a planilha e devolve os grupos que seriam gerados, sem abrir o Excel."""
        config.validate()
        dataframe = self._load_source(config)
        groups = self._split_groups(dataframe, config.report_type)
        return [
            GroupInfo(
                name=name,
                rows=len(group),
                output_name=config.report_type.output_filename(name),
            )
            for name, group in groups
        ]

    def run(self, config: JobConfig) -> JobResult:
        """Gera um dashboard por grupo e devolve o resumo da execução."""
        config.validate()

        started = time.perf_counter()
        result = JobResult(report_label=config.report_type.label)

        self._log(f"Lendo dados de origem: {config.source_file.name}", _ICON_INFO)
        dataframe = self._load_source(config)
        groups = self._split_groups(dataframe, config.report_type)
        if not groups:
            raise JobError(
                "Nenhum registro encontrado na aba "
                f"'{config.report_type.source_sheet}' da planilha de origem."
            )

        try:
            config.output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise JobError(
                "Não foi possível criar a pasta de saída:\n"
                f"{config.output_dir}\n\nDetalhe: {exc}"
            ) from exc

        self._check_cancel()
        self._inspect_template(config, dataframe, result)

        self._log(
            f"{len(groups)} grupo(s) encontrado(s) em "
            f"'{config.report_type.group_column}'.",
            _ICON_INFO,
        )

        xlwings = self._import_xlwings()
        pythoncom = self._init_com()

        app = None
        workbook = None
        temp_dir: str | None = None
        total = len(groups)
        used_names: dict[str, int] = {}
        reuse = config.report_type.reuse_template
        try:
            app = self._start_excel(xlwings)

            # Trabalha com uma cópia do template: evita conflito (arquivo
            # aberto no Excel / somente leitura).
            temp_dir = tempfile.mkdtemp(prefix="ins_dashboard_")
            template_copy = Path(temp_dir) / config.template_file.name
            self._copy_template(config.template_file, template_copy)

            if reuse:
                # Abre o template uma única vez; o modelo/pivôs ficam quentes
                # entre os grupos (grande ganho em templates com Data Model).
                workbook = self._open_template(
                    app, template_copy, config.template_file
                )
                app.api.Calculation = XL_CALCULATION_MANUAL

            for index, (group_name, group_data) in enumerate(groups, start=1):
                self._check_cancel()
                self._progress_cb(index, total, group_name)
                self._log(
                    f"[{index}/{total}] Gerando dashboard de {group_name} "
                    f"({len(group_data)} linha(s))...",
                    _ICON_INFO,
                )

                output_path = config.output_dir / self._allocate_output(
                    config.report_type, group_name, used_names
                )
                self._ensure_not_original(config, output_path)

                if not reuse:
                    workbook = self._open_template(
                        app, template_copy, config.template_file
                    )
                    app.api.Calculation = XL_CALCULATION_MANUAL

                # Recapturamos a cada grupo: o Resize invalida o proxy COM do
                # ListObject e o clear precisa atingir o corpo atual.
                sheet = self._template_sheet(workbook, config.report_type)
                table = self._template_table(sheet, config.report_type)
                last_column = self._template_last_column(
                    sheet, group_data.shape[1]
                )
                self._write_dashboard(
                    app,
                    workbook,
                    sheet,
                    table,
                    last_column,
                    group_data,
                    output_path,
                )

                result.outputs.append(
                    GroupResult(
                        group=group_name,
                        rows=len(group_data),
                        output_path=output_path,
                    )
                )
                result.total_rows += len(group_data)
                self._log(f"Salvo: {output_path.name}", _ICON_OK)

                if not reuse:
                    self._close_workbook(workbook)
                    workbook = None

            result.duration_seconds = time.perf_counter() - started
            self._log(
                f"Concluído: {result.dashboard_count} dashboard(s) gerado(s) "
                f"em {self._format_duration(result.duration_seconds)}.",
                _ICON_OK,
            )
            return result
        finally:
            if workbook is not None:
                self._close_workbook(workbook)
            if app is not None:
                self._close_excel(app)
            if temp_dir is not None:
                shutil.rmtree(temp_dir, ignore_errors=True)
            if pythoncom is not None:
                try:
                    pythoncom.CoUninitialize()
                except Exception:  # noqa: BLE001
                    pass

    # ------------------------------------------------------------------
    # Leitura e preparação dos dados
    # ------------------------------------------------------------------
    def _load_source(self, config: JobConfig) -> pd.DataFrame:
        report = config.report_type
        read_options: dict[str, object] = {"sheet_name": report.source_sheet}
        if _CALAMINE_AVAILABLE:
            read_options["engine"] = "calamine"
        try:
            # O notebook do transportador silencia UserWarning do openpyxl
            # (células com formatação/estilo incomum). Mantemos o mesmo cuidado.
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore", category=UserWarning, module="openpyxl"
                )
                dataframe = pd.read_excel(config.source_file, **read_options)
        except ValueError as exc:
            raise JobError(
                f"A aba '{report.source_sheet}' não foi encontrada em "
                f"'{config.source_file.name}'. Confira se o arquivo é o "
                f"relatório de {report.label}.",
            ) from exc
        except PermissionError as exc:
            raise JobError(
                "Sem permissão para ler o arquivo do relatório. Feche-o no "
                "Excel e tente novamente.\n\n"
                f"Arquivo: {config.source_file}"
            ) from exc
        except Exception as exc:  # noqa: BLE001 - erro de leitura do Excel
            raise JobError(
                "Não foi possível ler a planilha de origem. Verifique se o "
                "arquivo é um .xlsx válido e se não está corrompido.\n\n"
                f"Detalhe técnico: {exc}"
            ) from exc

        if dataframe.empty:
            raise JobError(
                "A planilha de origem não possui dados na aba "
                f"'{report.source_sheet}'."
            )
        return dataframe

    def _prepare_dataframe(
        self, dataframe: pd.DataFrame, report: ReportType
    ) -> pd.DataFrame:
        columns = list(dataframe.columns)

        if report.uses_keep_list:
            missing = [c for c in report.keep_columns if c not in columns]
            if missing:
                raise JobError(
                    "A planilha de origem não possui as colunas esperadas para "
                    f"{report.label}:\n- " + "\n- ".join(missing)
                )
            prepared = dataframe[list(report.keep_columns)].copy()
        else:
            if report.group_column not in columns:
                raise JobError(
                    f"A coluna de agrupamento '{report.group_column}' não foi "
                    f"encontrada na planilha. Colunas disponíveis:\n- "
                    + "\n- ".join(map(str, columns))
                )
            present_drop = [c for c in report.drop_columns if c in columns]
            absent_drop = [c for c in report.drop_columns if c not in columns]
            if absent_drop:
                self._log(
                    "Colunas que seriam removidas não existem na origem "
                    "(seguindo sem elas): " + ", ".join(absent_drop),
                    _ICON_WARNING,
                )
            prepared = dataframe.drop(columns=present_drop).copy()

        missing_groups = prepared[report.group_column].isna().sum()
        if missing_groups:
            self._log(
                f"{int(missing_groups)} linha(s) sem valor em "
                f"'{report.group_column}' serão ignoradas.",
                _ICON_WARNING,
            )
            prepared = prepared[prepared[report.group_column].notna()]

        if report.uppercase_group_values:
            prepared[report.group_column] = (
                prepared[report.group_column].astype(str).str.upper()
            )

        return prepared

    def _split_groups(
        self, dataframe: pd.DataFrame, report: ReportType
    ) -> list[tuple[str, pd.DataFrame]]:
        prepared = self._prepare_dataframe(dataframe, report)
        if prepared.empty:
            return []

        groups: list[tuple[str, pd.DataFrame]] = []
        for raw_name, group in prepared.groupby(
            report.group_column, sort=True, dropna=True
        ):
            name = str(raw_name).strip()
            if not name or name.lower() in {"nan", "none"}:
                name = "SEM IDENTIFICACAO"
            groups.append((name.upper(), group.copy()))
        return groups

    def _inspect_template(
        self, config: JobConfig, dataframe: pd.DataFrame, result: JobResult
    ) -> None:
        """Valida aba/cabeçalho do template antes de abrir o Excel."""
        report = config.report_type
        try:
            import openpyxl

            workbook = openpyxl.load_workbook(
                config.template_file, read_only=True, data_only=True
            )
        except Exception as exc:  # noqa: BLE001
            raise JobError(
                "Não foi possível abrir o template do dashboard. Verifique se "
                "o arquivo é válido e se não está aberto no Excel.\n\n"
                f"Detalhe técnico: {exc}"
            ) from exc

        try:
            if report.template_sheet not in workbook.sheetnames:
                raise JobError(
                    f"O template não possui a aba '{report.template_sheet}'. "
                    "Abas encontradas: " + ", ".join(workbook.sheetnames)
                )
            worksheet = workbook[report.template_sheet]
            header = next(
                worksheet.iter_rows(min_row=1, max_row=1, values_only=True),
                (),
            )
        finally:
            workbook.close()

        template_columns = [
            str(value).strip() for value in header if value is not None
        ]
        expected = list(dataframe.columns)
        if template_columns and len(template_columns) >= len(expected):
            mismatches = [
                f"coluna {i + 1}: template='{tpl}' / dados='{data}'"
                for i, (tpl, data) in enumerate(
                    zip(template_columns, expected)
                )
                if tpl.casefold() != str(data).strip().casefold()
            ]
            if mismatches:
                message = (
                    "O cabeçalho do template difere dos dados de origem. "
                    "Confira se o template escolhido corresponde ao tipo de "
                    "relatório:\n- " + "\n- ".join(mismatches[:8])
                )
                if len(mismatches) > 8:
                    message += f"\n- ... e mais {len(mismatches) - 8}."
                result.warnings.append(message)
                self._log(message, _ICON_WARNING)
        elif template_columns and len(template_columns) < len(expected):
            message = (
                f"O template possui {len(template_columns)} coluna(s) na linha 1, "
                f"mas os dados têm {len(expected)}. Confira o template escolhido."
            )
            result.warnings.append(message)
            self._log(message, _ICON_WARNING)

    # ------------------------------------------------------------------
    # Excel / xlwings
    # ------------------------------------------------------------------
    def _import_xlwings(self):
        if self._xlwings is not None:
            return self._xlwings
        if sys.platform != "win32":
            raise JobError(
                "A geração de dashboards usa automação do Microsoft Excel "
                "(xlwings) e só funciona no Windows."
            )
        try:
            self._xlwings = importlib.import_module("xlwings")
        except ImportError as exc:
            raise JobError(
                "A biblioteca 'xlwings' não está instalada. Instale com:\n\n"
                "    pip install xlwings"
            ) from exc
        return self._xlwings

    @staticmethod
    def _init_com():
        if sys.platform != "win32":
            return None
        try:
            import pythoncom
        except ImportError:
            return None
        try:
            pythoncom.CoInitialize()
        except Exception:  # noqa: BLE001
            return None
        return pythoncom

    @staticmethod
    def _start_excel(xlwings):
        """Abre (uma única vez) a instância invisível do Excel."""
        try:
            app = xlwings.App(visible=False, add_book=False)
        except Exception as exc:  # noqa: BLE001 - erro do Excel/COM
            raise JobError(
                "Não foi possível abrir o Microsoft Excel. Verifique se o "
                "Excel está instalado e se não há uma janela modal "
                "(ex.: caixa de diálogo) bloqueando a automação.\n\n"
                f"Detalhe técnico: {exc}"
            ) from exc
        app.display_alerts = False
        app.screen_updating = False
        return app

    @staticmethod
    def _copy_template(source: Path, destination: Path) -> None:
        """Copia o template para uma pasta temporária antes de abrir."""
        try:
            shutil.copy2(source, destination)
        except OSError as exc:
            raise JobError(
                "Não foi possível preparar o template para a geração. Feche o "
                "arquivo se estiver aberto no Excel e tente novamente.\n\n"
                f"Template: {source}\n\nDetalhe técnico: {exc}"
            ) from exc

    @staticmethod
    def _open_template(app, template_copy: Path, original: Path):
        try:
            return app.books.open(str(template_copy))
        except Exception as exc:  # noqa: BLE001
            raise JobError(
                "Não foi possível abrir o template no Excel. Feche o "
                "arquivo se estiver aberto e tente novamente.\n\n"
                f"Template: {original}\n"
                f"Detalhe técnico: {exc}"
            ) from exc

    def _template_sheet(self, workbook, report: ReportType):
        try:
            return workbook.sheets[report.template_sheet]
        except Exception as exc:  # noqa: BLE001
            available = self._sheet_names(workbook)
            raise JobError(
                f"A aba '{report.template_sheet}' não existe no template. "
                f"Abas encontradas: {available or 'nenhuma'}."
            ) from exc

    def _template_table(self, sheet, report: ReportType):
        try:
            return sheet.tables[report.template_table]
        except Exception as exc:  # noqa: BLE001
            available = self._table_names(sheet)
            raise JobError(
                f"A tabela '{report.template_table}' não existe na aba "
                f"'{report.template_sheet}' do template. Tabelas "
                f"encontradas: {available or 'nenhuma'}."
            ) from exc

    @staticmethod
    def _template_last_column(sheet, total_columns: int) -> str:
        address = str(sheet.range((1, total_columns)).address)
        return address.split("$")[1]

    def _write_dashboard(
        self,
        app,
        workbook,
        sheet,
        table,
        last_column: str,
        group_data: pd.DataFrame,
        output_path: Path,
    ) -> None:
        """Preenche o workbook já aberto e salva uma cópia para o grupo."""
        row_count = len(group_data)

        # Manual enquanto escreve (evita recalcular a cada célula). O modo é
        # devolvido para automático antes de salvar: o Excel grava o estado em
        # <calcPr calcMode>, e um arquivo salvo em manual não avalia os campos
        # TxLink dos cards do Resumo ao abrir (números em branco).
        app.api.Calculation = XL_CALCULATION_MANUAL

        if table.data_body_range is not None:
            table.data_body_range.clear_contents()

        # Escreve a partir de A2 (sem cabeçalho nem índice).
        sheet.range("A2").options(index=False, header=False).value = group_data

        table.resize(sheet.range(f"A1:{last_column}{row_count + 1}"))

        app.api.Calculation = XL_CALCULATION_AUTOMATIC
        try:
            workbook.api.RefreshAll()
        except Exception as exc:  # noqa: BLE001 - nem todo template tem consultas
            self._log(
                "Aviso: o Excel não conseguiu atualizar as consultas do "
                f"template ({exc}). O dashboard foi salvo mesmo assim.",
                _ICON_WARNING,
            )
        # Não voltar para manual aqui: o próximo grupo reativa o modo manual
        # no início de _write_dashboard. Salvar em manual gravaria
        # calcMode="manual" no dashboard.

        self._check_cancel()
        self._save_workbook(workbook, output_path)

    @staticmethod
    def _save_workbook(workbook, output_path: Path) -> None:
        # Regenerações sobrescrevem o dashboard anterior. Removemos o arquivo
        # antes do SaveCopyAs para o Excel não exibir o diálogo "já existe".
        # SaveCopyAs mantém o template em memória intacto para o próximo grupo
        # (workbook.save renomearia o livro em uso).
        if output_path.exists():
            try:
                output_path.unlink()
            except OSError as exc:
                raise JobError(
                    "O dashboard anterior existe e não pôde ser substituído. "
                    "Feche o arquivo no Excel e tente novamente.\n\n"
                    f"Destino: {output_path}"
                ) from exc
        try:
            workbook.api.SaveCopyAs(str(output_path))
        except PermissionError as exc:
            raise JobError(
                "Sem permissão para salvar o dashboard. Feche o arquivo se ele "
                "estiver aberto no Excel e tente novamente.\n\n"
                f"Destino: {output_path}"
            ) from exc
        except Exception as exc:  # noqa: BLE001
            raise JobError(
                "Não foi possível salvar o dashboard.\n\n"
                f"Destino: {output_path}\n"
                f"Detalhe técnico: {exc}"
            ) from exc

    @staticmethod
    def _sheet_names(workbook) -> str:
        try:
            return ", ".join(sheet.name for sheet in workbook.sheets)
        except Exception:  # noqa: BLE001
            return ""

    @staticmethod
    def _table_names(sheet) -> str:
        try:
            return ", ".join(table.name for table in sheet.tables)
        except Exception:  # noqa: BLE001
            return ""

    @staticmethod
    def _close_workbook(workbook) -> None:
        try:
            workbook.close()
        except Exception:  # noqa: BLE001
            pass

    def _close_excel(self, app) -> None:
        try:
            app.display_alerts = True
        except Exception:  # noqa: BLE001
            pass
        try:
            app.screen_updating = True
        except Exception:  # noqa: BLE001
            pass
        try:
            app.quit()
        except Exception:  # noqa: BLE001
            pass

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------
    def _allocate_output(
        self,
        report: ReportType,
        group_name: str,
        used_names: dict[str, int],
    ) -> Path:
        base_name = report.output_filename(group_name)
        stem = Path(base_name).stem
        count = used_names.get(stem, 0) + 1
        used_names[stem] = count
        if count == 1:
            return Path(base_name)
        return Path(f"{stem} ({count}).xlsx")

    def _check_cancel(self) -> None:
        if self._cancel_cb():
            raise JobCancelled("Geração cancelada pelo usuário.")

    @staticmethod
    def _ensure_not_original(config: JobConfig, output_path: Path) -> None:
        protected = {
            config.source_file.resolve(),
            config.template_file.resolve(),
        }
        if output_path.resolve() in protected:
            raise JobError(
                "O nome do dashboard gerado coincidiria com um arquivo "
                "original e o sobrescreveria:\n\n"
                f"{output_path}\n\nEscolha outra pasta de saída."
            )

    def _log(self, message: str, level: str = _ICON_INFO) -> None:
        self._log_cb(message, level)

    @staticmethod
    def _format_duration(seconds: float) -> str:
        if seconds < 60:
            return f"{seconds:.1f} s"
        minutes, remaining = divmod(int(seconds), 60)
        return f"{minutes} min {remaining} s"


__all__ = [
    "DashboardProcessor",
    "JobCancelled",
    "JobError",
    "JobConfig",
    "JobResult",
    "GroupInfo",
    "GroupResult",
]
