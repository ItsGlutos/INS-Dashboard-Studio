"""Teste rápido do backend (não abre o Excel).

Gera planilhas sintéticas e valida a leitura, o agrupamento, a validação de
configuração e os avisos de cabeçalho do template.

Execução (a partir de ins_dashboard_app)::

    python -m testes.smoke_test
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.worksheet.table import Table, TableStyleInfo

from backend import DashboardProcessor, JobConfig, JobError, get_report_type
from backend.models import JobResult
from backend.reports import MOTORISTA, TRANSPORTADOR, sanitize_filename


def _column_letter(index: int) -> str:
    letters = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def _make_template(path: Path, sheet: str, table: str, columns: list[str]) -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = sheet
    worksheet.append(columns)
    worksheet.append([None] * len(columns))
    reference = f"A1:{_column_letter(len(columns))}2"
    new_table = Table(displayName=table, ref=reference)
    new_table.tableStyleInfo = TableStyleInfo(
        name="TableStyleMedium2", showRowStripes=True
    )
    worksheet.add_table(new_table)
    workbook.save(path)


def _build_fixtures(base: Path) -> tuple[Path, Path, Path, Path]:
    # ----- Motorista -------------------------------------------------
    motorista_rows = []
    for name in ["João", "Maria"]:
        for month in ["Jan", "Fev"]:
            motorista_rows.append(
                {
                    "Mês": month,
                    "Rota/Roteiro": "R1",
                    "Tipo_Operação": "Entrega",
                    "Apelido": name,
                    "CD": "SC",
                    "Embarcada": 1,
                    "Entrega Meta": 10,
                    "Ocorrencias": 1,
                    "Ocorrencias_Validas": 1,
                    "Viagens": 2,
                    "Logins": 3,
                    "Volumes": 4,
                    "Volumetria": 5,
                    "Transit_Time": 6,
                }
            )
    motorista_source = base / "motorista.xlsx"
    with pd.ExcelWriter(motorista_source) as writer:
        pd.DataFrame(motorista_rows).to_excel(
            writer, sheet_name="INS", index=False
        )

    motorista_template = base / "template_motorista.xlsx"
    _make_template(
        motorista_template, "INS", "INS", list(MOTORISTA.keep_columns)
    )

    # ----- Transportador --------------------------------------------
    transportador_columns = [
        "TRANSPORTADOR",
        "TIPO DA ROTA",
        "CD + Transportadora",
        "CD +  TRANSPORTADORA + TIPO DA ROTA",
        "CNPJ",
        "EXTRAVIO",
        "AVARIA",
        "FALTA DE VOLUME",
        "PENDÊNCIA DE MANIFESTO",
        "ROUBO OU ACIDENTE",
        "TT CFD",
        "Cont",
        "VALOR CARREGADO",
        "Mês",
        "Viagens",
    ]
    transportador_rows = []
    for name in ["Alfa", "Beta"]:
        transportador_rows.append(
            {
                **{column: "x" for column in transportador_columns},
                "TRANSPORTADOR": name,
                "Mês": "Jan",
                "Viagens": 7,
            }
        )
    transportador_source = base / "transportador.xlsx"
    with pd.ExcelWriter(transportador_source) as writer:
        pd.DataFrame(transportador_rows).to_excel(
            writer, sheet_name="INS", index=False
        )

    transportador_columns_keep = [
        column
        for column in transportador_columns
        if column not in TRANSPORTADOR.drop_columns
    ]
    transportador_template = base / "template_transportador.xlsx"
    _make_template(
        transportador_template, "Dados", "Tabela3", transportador_columns_keep
    )

    return (
        motorista_source,
        motorista_template,
        transportador_source,
        transportador_template,
    )


def main() -> int:
    logs: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        (
            motorista_source,
            motorista_template,
            transportador_source,
            transportador_template,
        ) = _build_fixtures(base)
        output = base / "saida"
        output.mkdir()

        processor = DashboardProcessor(
            on_log=lambda mensagem, nivel: logs.append(f"{nivel}: {mensagem}")
        )

        # ---- descoberta de grupos ----------------------------------
        motorista_config = JobConfig(
            get_report_type("motorista"),
            motorista_source,
            motorista_template,
            output,
        )
        groups = processor.discover_groups(motorista_config)
        assert [g.name for g in groups] == ["JOÃO", "MARIA"], groups
        assert all(g.rows == 2 for g in groups), groups
        assert groups[0].output_name == "INS do Motorista - JOÃO.xlsx", groups[0]

        transportador_config = JobConfig(
            get_report_type("transportador"),
            transportador_source,
            transportador_template,
            output,
        )
        groups = processor.discover_groups(transportador_config)
        assert [g.name for g in groups] == ["ALFA", "BETA"], groups

        # ---- validações de configuração ----------------------------
        try:
            JobConfig(
                get_report_type("motorista"),
                base / "nao_existe.xlsx",
                motorista_template,
                output,
            ).validate()
        except JobError as exc:
            assert "não encontrado" in str(exc)
        else:
            raise AssertionError("JobConfig deveria falhar com arquivo inexistente")

        # ---- cabeçalho incompatível gera aviso ---------------------
        result = JobResult(report_label="teste")
        processor._inspect_template(
            transportador_config,
            pd.DataFrame(columns=["COLUNA ERRADA"] * 3),
            result,
        )
        assert result.warnings, "template incompatível deveria gerar aviso"

        # ---- nomes de arquivo seguros ------------------------------
        assert sanitize_filename('A/B:C*D?E"F<G>H|I') == "A_B_C_D_E_F_G_H_I"
        assert sanitize_filename("  NOME.  ") == "NOME"
        assert sanitize_filename("") == "SEM_NOME"

        print("OK: backend validado sem abrir o Excel.")
        print(f"Logs capturados: {len(logs)}")
        for line in logs[-3:]:
            print(f"  {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
