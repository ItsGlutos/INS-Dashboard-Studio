"""Testes de performance/comportamento do motor de geração (sem abrir o Excel).

Cobrem as duas mudanças da Fase 1:

1. o template é aberto **uma vez** por execução e cada grupo é salvo com
   ``SaveCopyAs`` (workbook reaproveitado), em vez de abrir/fechar por grupo;
2. a planilha de origem é lida com ``calamine`` quando disponível.

Execução::

    python -m unittest testes.processor_perf_test -v
"""

from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from backend import DashboardProcessor, JobConfig, get_report_type
from backend.processor import XL_CALCULATION_AUTOMATIC, XL_CALCULATION_MANUAL
from backend.reports import MOTORISTA
from testes.smoke_test import _build_fixtures, _make_template


class _FakeRange:
    def __init__(self, sheet: "_FakeSheet", address: str = "A1") -> None:
        self._sheet = sheet
        self._address = address

    @property
    def address(self) -> str:
        return "$A$1"

    def options(self, **_kwargs) -> "_FakeRange":
        return self

    @property
    def value(self):
        return None

    @value.setter
    def value(self, value) -> None:
        self._sheet.write_frame(value)

    def clear_contents(self) -> None:
        self._sheet.cleared += 1


class _FakeTable:
    """Simula o ListObject do Excel: cada Resize invalida o objeto anterior.

    O objeto antigo continua enxergando o corpo de tabela que tinha quando foi
    capturado — é o que acontece com o proxy COM guardado em cache.
    """

    def __init__(self, sheet: "_FakeSheet", last_row: int) -> None:
        self._sheet = sheet
        self._last_row = last_row

    @property
    def data_body_range(self) -> "_FakeBodyRange":
        return _FakeBodyRange(self._sheet, self._last_row)

    def resize(self, rng: _FakeRange) -> None:
        self._sheet.resize_table(int(rng._address.rsplit(":", 1)[-1].lstrip("ABCDEFGHIJKLMNOPQRSTUVWXYZ")))


class _FakeBodyRange:
    def __init__(self, sheet: "_FakeSheet", last_row: int) -> None:
        self._sheet = sheet
        self._last_row = last_row

    def clear_contents(self) -> None:
        self._sheet.clear_rows(2, self._last_row)
        self._sheet.cleared += 1


class _FakeTables:
    def __init__(self, sheet: "_FakeSheet") -> None:
        self._sheet = sheet

    def __getitem__(self, _name: str) -> _FakeTable:
        return self._sheet.current_table


class _FakeSheet:
    def __init__(self, total_columns: int = 14) -> None:
        self.total_columns = total_columns
        self.cells: dict[tuple[int, int], object] = {}
        self.written: list = []
        self.cleared = 0
        self._last_row = 3
        self.current_table = _FakeTable(self, self._last_row)
        self.tables = _FakeTables(self)

    def range(self, arg) -> _FakeRange:
        if isinstance(arg, tuple):
            return _FakeRange(self, "A1")
        return _FakeRange(self, str(arg))

    def write_frame(self, frame) -> None:
        self.written.append(frame)
        values = frame.values if hasattr(frame, "values") else frame
        for offset, row in enumerate(values, start=2):
            for column, value in enumerate(row, start=1):
                self.cells[(offset, column)] = value

    def clear_rows(self, first: int, last: int) -> None:
        for key in list(self.cells):
            if first <= key[0] <= last:
                del self.cells[key]

    def resize_table(self, last_row: int) -> None:
        self._last_row = last_row
        self.current_table = _FakeTable(self, last_row)


class _FakeSheets:
    def __init__(self) -> None:
        self.sheet = _FakeSheet()

    def __getitem__(self, _name: str) -> _FakeSheet:
        return self.sheet


class _FakeBookApi:
    def __init__(self, app: "_FakeApp") -> None:
        self._app = app
        self.saves: list[str] = []
        self.refreshes = 0
        self.calculation_at_save: list[int | None] = []

    def RefreshAll(self) -> None:  # noqa: N802 - nome da API do Excel
        self.refreshes += 1

    def SaveCopyAs(self, path: str) -> None:  # noqa: N802 - nome da API do Excel
        # O modo de cálculo vigente é gravado no arquivo (<calcPr calcMode>).
        # Salvar em manual deixa os campos vinculados (cards do Resumo) em
        # branco até o usuário forçar um recálculo.
        self.calculation_at_save.append(self._app.api.Calculation)
        self.saves.append(path)


class _FakeBook:
    def __init__(self, app: "_FakeApp") -> None:
        self.sheets = _FakeSheets()
        self.api = _FakeBookApi(app)
        self.close_calls = 0
        self.save_calls: list[str] = []

    def save(self, path: str) -> None:
        self.save_calls.append(path)

    def close(self) -> None:
        self.close_calls += 1


class _FakeBooks:
    def __init__(self, app: "_FakeApp") -> None:
        self._app = app
        self.opened: list[str] = []
        self.books: list[_FakeBook] = []

    def open(self, path: str) -> _FakeBook:  # noqa: A003 - nome da API do xlwings
        self.opened.append(path)
        book = _FakeBook(self._app)
        self.books.append(book)
        return book


class _FakeAppApi:
    def __init__(self) -> None:
        self.Calculation = None


class _FakeApp:
    def __init__(self, **_kwargs) -> None:
        self.api = _FakeAppApi()
        self.books = _FakeBooks(self)
        self.quit_calls = 0
        self.display_alerts = True
        self.screen_updating = True

    def quit(self) -> None:
        self.quit_calls += 1


class _FakeXlwings:
    def __init__(self) -> None:
        self.apps: list[_FakeApp] = []

    def App(self, **kwargs) -> _FakeApp:  # noqa: N802 - nome da API do xlwings
        app = _FakeApp(**kwargs)
        self.apps.append(app)
        return app


class TemplateReuseTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        base = Path(self._tmp.name)
        (
            self.source,
            self.template,
            _transportador_source,
            _transportador_template,
        ) = _build_fixtures(base)
        self.output = base / "saida"
        self.output.mkdir()
        self.report = replace(MOTORISTA, reuse_template=True)
        self.config = JobConfig(
            self.report, self.source, self.template, self.output
        )

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_template_aberto_uma_vez_e_salvo_com_copia_por_grupo(self) -> None:
        fake = _FakeXlwings()
        processor = DashboardProcessor()
        processor._xlwings = fake

        with patch.object(
            DashboardProcessor, "_init_com", return_value=None
        ):
            result = processor.run(self.config)

        self.assertEqual(result.dashboard_count, 2)
        self.assertEqual(len(fake.apps), 1, "deve abrir uma única instância do Excel")

        app = fake.apps[0]
        book = app.books.books[0]
        self.assertEqual(
            len(app.books.opened), 1, "o template deve ser aberto uma única vez"
        )
        self.assertEqual(len(book.api.saves), 2, "um SaveCopyAs por grupo")
        self.assertEqual(book.api.refreshes, 2, "um RefreshAll por grupo")
        self.assertEqual(book.close_calls, 1, "fechar o workbook só no final")
        self.assertEqual(app.quit_calls, 1, "fechar o Excel só no final")
        self.assertEqual(
            [Path(path).name for path in book.api.saves],
            [
                "INS do Motorista - JOÃO.xlsx",
                "INS do Motorista - MARIA.xlsx",
            ],
        )
        self.assertFalse(
            [item for item in result.outputs if not item.output_path.name],
            result.outputs,
        )
        self.assertEqual(app.api.Calculation, XL_CALCULATION_AUTOMATIC)

    def test_salva_cada_grupo_com_calculo_automatico(self) -> None:
        """Salvar em manual grava calcMode="manual" e apaga os cards do Resumo.

        Os números dos cards são campos ``TxLink`` (formas ligadas às células
        do Gerencial). Com o arquivo em cálculo manual o Excel não os avalia ao
        abrir e eles ficam em branco até alguém forçar um recálculo.
        """
        fake = _FakeXlwings()
        processor = DashboardProcessor()
        processor._xlwings = fake

        with patch.object(
            DashboardProcessor, "_init_com", return_value=None
        ):
            processor.run(self.config)

        api = fake.apps[0].books.books[0].api
        self.assertEqual(
            api.calculation_at_save,
            [XL_CALCULATION_AUTOMATIC, XL_CALCULATION_AUTOMATIC],
            "todo SaveCopyAs deve acontecer com o cálculo automático",
        )

    def test_usa_copia_temporaria_do_template(self) -> None:
        fake = _FakeXlwings()
        processor = DashboardProcessor()
        processor._xlwings = fake

        with patch.object(
            DashboardProcessor, "_init_com", return_value=None
        ):
            processor.run(self.config)

        aberto = Path(fake.apps[0].books.opened[0])
        self.assertNotEqual(aberto, self.template)
        self.assertEqual(aberto.suffix, self.template.suffix)
        self.assertFalse(aberto.exists(), "a cópia temporária deve ser removida")


class FreshTemplateTest(unittest.TestCase):
    """Motorista mantém abrir/fechar por grupo (abas ocultas com estado)."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        base = Path(self._tmp.name)
        (
            self.source,
            self.template,
            _transportador_source,
            _transportador_template,
        ) = _build_fixtures(base)
        self.output = base / "saida"
        self.output.mkdir()
        self.config = JobConfig(
            get_report_type("motorista"), self.source, self.template, self.output
        )

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_motorista_reabre_o_template_a_cada_grupo(self) -> None:
        fake = _FakeXlwings()
        processor = DashboardProcessor()
        processor._xlwings = fake

        with patch.object(
            DashboardProcessor, "_init_com", return_value=None
        ):
            resultado = processor.run(self.config)

        self.assertEqual(resultado.dashboard_count, 2)
        self.assertEqual(len(fake.apps), 1, "uma única instância do Excel")
        app = fake.apps[0]
        self.assertEqual(
            len(app.books.opened), 2, "um template por grupo (sem reuso)"
        )
        self.assertEqual(
            [book.close_calls for book in app.books.books], [1, 1]
        )
        self.assertEqual(
            [len(book.api.saves) for book in app.books.books], [1, 1]
        )
        self.assertEqual(app.quit_calls, 1)


class TableShrinkTest(unittest.TestCase):
    """O grupo menor não pode herdar as linhas escritas pelo grupo anterior."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        base = Path(self._tmp.name)
        colunas = list(MOTORISTA.keep_columns)

        linhas = []
        for _ in range(5):
            linhas.append({**{c: 1 for c in colunas}, "Apelido": "João"})
        for _ in range(2):
            linhas.append({**{c: 2 for c in colunas}, "Apelido": "Maria"})

        self.source = base / "motorista_grande_pequeno.xlsx"
        with pd.ExcelWriter(self.source) as writer:
            pd.DataFrame(linhas).to_excel(writer, sheet_name="INS", index=False)

        self.template = base / "template_motorista.xlsx"
        _make_template(self.template, "INS", "INS", colunas)
        self.base = base

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_grupo_menor_nao_herda_linhas_do_grupo_anterior(self) -> None:
        fake = _FakeXlwings()
        processor = DashboardProcessor()
        processor._xlwings = fake
        config = JobConfig(
            replace(MOTORISTA, reuse_template=True),
            self.source,
            self.template,
            self.base,
        )

        with patch.object(
            DashboardProcessor, "_init_com", return_value=None
        ):
            processor.run(config)

        sheet = fake.apps[0].books.books[0].sheets.sheet
        linhas_com_valor = {linha for linha, _coluna in sheet.cells}
        # cabeçalho (1) + 2 linhas da Maria
        self.assertEqual(
            max(linhas_com_valor),
            3,
            "sobrou linha do grupo anterior (João) no arquivo da Maria",
        )
        self.assertEqual(
            {sheet.cells[(2, 1)], sheet.cells[(3, 1)]},
            {2},
            "as linhas finais devem conter apenas os dados da Maria",
        )


class SourceReadTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        base = Path(self._tmp.name)
        (
            self.source,
            self.template,
            _transportador_source,
            _transportador_template,
        ) = _build_fixtures(base)
        self.config = JobConfig(
            get_report_type("motorista"), self.source, self.template, base
        )

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_le_origem_com_calamine_quando_disponivel(self) -> None:
        processor = DashboardProcessor()
        esperado = pd.DataFrame({"COLUNA": [1]})
        with patch(
            "backend.processor._CALAMINE_AVAILABLE", True, create=True
        ), patch(
            "backend.processor.pd.read_excel", return_value=esperado
        ) as read_mock:
            lido = processor._load_source(self.config)

        self.assertTrue(lido.equals(esperado))
        self.assertEqual(
            read_mock.call_args.kwargs.get("engine"),
            "calamine",
            "deve usar calamine para leitura rápida",
        )

    def test_sem_calamine_nao_forca_engine(self) -> None:
        processor = DashboardProcessor()
        esperado = pd.DataFrame({"COLUNA": [1]})
        with patch(
            "backend.processor._CALAMINE_AVAILABLE", False, create=True
        ), patch(
            "backend.processor.pd.read_excel", return_value=esperado
        ) as read_mock:
            processor._load_source(self.config)

        self.assertNotIn("engine", read_mock.call_args.kwargs)


if __name__ == "__main__":
    unittest.main(verbosity=2)
