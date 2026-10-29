"""Testes do verificador estrutural dos dashboards."""

from __future__ import annotations

import re
import shutil
import tempfile
import unittest
import zipfile
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

    def test_calculo_manual_e_reportado(self) -> None:
        """calcMode="manual" deixa os cards TxLink em branco no Excel."""
        manual = self.base / "manual.xlsx"
        _marcar_manual(self.referencia, manual)

        self.assertEqual(inventariar(manual).calculo, "manual")
        problemas = comparar(
            inventariar(self.referencia), inventariar(manual)
        )
        self.assertTrue(
            any(p.startswith("modo de cálculo:") for p in problemas), problemas
        )


def _marcar_manual(origem: Path, destino: Path) -> None:
    with zipfile.ZipFile(origem) as entrada, zipfile.ZipFile(
        destino, "w", zipfile.ZIP_DEFLATED
    ) as saida:
        for item in entrada.infolist():
            dados = entrada.read(item.filename)
            if item.filename == "xl/workbook.xml":
                xml = dados.decode("utf-8")
                if "<calcPr" in xml:
                    xml = re.sub(
                        r"<calcPr([^>]*)/>",
                        r'<calcPr\1 calcMode="manual"/>',
                        xml,
                        count=1,
                    )
                else:
                    xml = xml.replace(
                        "</workbook>",
                        '<calcPr calcId="1" calcMode="manual"/></workbook>',
                    )
                dados = xml.encode("utf-8")
            saida.writestr(item, dados)


if __name__ == "__main__":
    unittest.main(verbosity=2)
