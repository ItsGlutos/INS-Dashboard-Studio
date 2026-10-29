"""Testes do verificador estrutural dos dashboards."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook
from openpyxl.chart import LineChart, Reference

from testes.estrutura_dashboard import comparar, inventariar


def _workbook(caminho: Path, com_grafico: bool) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Resumo"
    ws["A1"] = "Mês"
    ws["A2"] = 0.5
    if com_grafico:
        grafico = LineChart()
        grafico.add_data(
            Reference(ws, min_col=1, min_row=1, max_row=2), titles_from_data=True
        )
        ws.add_chart(grafico, "C1")
    wb.save(caminho)
    wb.close()


class EstruturaTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        self.referencia = self.base / "referencia.xlsx"
        _workbook(self.referencia, com_grafico=True)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_arquivo_identico_nao_tem_diferencas(self) -> None:
        copia = self.base / "copia.xlsx"
        shutil.copy2(self.referencia, copia)
        self.assertEqual(comparar(inventariar(self.referencia), inventariar(copia)), [])

    def test_grafico_ausente_e_reportado(self) -> None:
        sem_grafico = self.base / "sem_grafico.xlsx"
        _workbook(sem_grafico, com_grafico=False)

        problemas = comparar(
            inventariar(self.referencia), inventariar(sem_grafico)
        )

        self.assertTrue(
            any(p.startswith("graficos:") for p in problemas), problemas
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
