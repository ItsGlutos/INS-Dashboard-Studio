"""Teste ponta a ponta: gera dashboards reais usando o Microsoft Excel.

Requer Windows com Excel instalado e um template com tabela. Usa planilhas
sintéticas (criadas em pasta temporária), portanto não toca nos arquivos
originais do projeto.

Execução (a partir de ins_dashboard_app)::

    python -m testes.e2e_excel
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from backend import DashboardProcessor, JobConfig, JobError, get_report_type
from testes.smoke_test import _build_fixtures


def main() -> int:
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

        def log(mensagem: str, nivel: str) -> None:
            # Evita problemas de console no Windows; o app usa Qt.
            print(f"[{nivel}] {mensagem}".encode("ascii", "replace").decode())

        for key, source, template in [
            ("motorista", motorista_source, motorista_template),
            ("transportador", transportador_source, transportador_template),
        ]:
            processor = DashboardProcessor(on_log=log)
            config = JobConfig(
                get_report_type(key), source, template, output
            )
            try:
                result = processor.run(config)
            except JobError as exc:
                print(f"FALHOU ({key}): {exc}".encode("ascii", "replace").decode())
                return 1
            assert result.dashboard_count == 2, result
            for item in result.outputs:
                assert item.output_path.is_file(), item.output_path
                assert item.output_path.parent == output, item.output_path
                print(f"gerado: {item.output_path.name}")
        print("OK: geracao completa validada no Excel.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
