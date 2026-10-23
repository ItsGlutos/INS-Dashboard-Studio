"""Smoke test offscreen da aba Envios (não abre o Outlook).

Execução (a partir de ``ins_dashboard_app``)::

    python -m testes.envios_ui_smoke

Gera planilhas/arquivos sintéticos, monta o plano e valida a tabela de
confirmação. Também salva uma captura em ``_saida_teste/envios.png``.
"""

from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pandas as pd  # noqa: E402
from PyQt6.QtCore import Qt  # noqa: E402
from PyQt6.QtGui import QFont  # noqa: E402
from PyQt6.QtTest import QTest  # noqa: E402
from PyQt6.QtWidgets import QApplication, QDialog  # noqa: E402

from backend.envios import montar_plano  # noqa: E402
from ui import envios_tab as envios_tab_module  # noqa: E402
from ui import main_window as main_window_module  # noqa: E402
from ui.envios_dialog import EnviosConfirmDialog  # noqa: E402
from ui.main_window import MainWindow  # noqa: E402
from ui.theme import APP_FONT, build_stylesheet  # noqa: E402


class _FakeSettings:
    """QSettings em memória para não poluir o registro do Windows."""

    _store: dict[tuple[str, str], dict[str, object]] = {}

    def __init__(self, organization: str, application: str) -> None:
        self._data = self._store.setdefault((organization, application), {})

    def value(self, key: str, default: object = None) -> object:
        return self._data.get(key, default)

    def setValue(self, key: str, value: object) -> None:
        self._data[key] = value


def _fixtures(base: Path) -> tuple[Path, Path]:
    contatos = base / "contatos.xlsx"
    with pd.ExcelWriter(contatos) as writer:
        pd.DataFrame(
            [
                {"Transportadora": "Alfa", "E-mail": "a@alfa.com"},
                {"Transportadora": "Beta", "E-mail": "b@beta.com"},
                {"Transportadora": "Gama", "E-mail": ""},
            ]
        ).to_excel(writer, sheet_name="Contatos", index=False)

    pasta = base / "arquivos"
    pasta.mkdir()
    for nome in ("Alfa", "Beta", "Gama"):
        (pasta / f"INS do Transportador - {nome}.xlsx").write_bytes(b"x")
    return contatos, pasta


class _FakeDialog:
    """Substitui o diálogo modal nos testes (não bloqueia o event loop)."""

    aceitar = True

    def __init__(self, plano, debug: bool = False, parent=None) -> None:
        self.plano = plano
        self.debug = debug

    def exec(self) -> int:
        return int(
            QDialog.DialogCode.Accepted
            if self.aceitar
            else QDialog.DialogCode.Rejected
        )

    def selected_keys(self) -> list[str]:
        return [grupo.chave for grupo in self.plano.prontos]


def _wait(envios, app: QApplication, timeout: float = 30.0) -> None:
    limite = time.monotonic() + timeout
    while envios.is_running and time.monotonic() < limite:
        app.processEvents()
        time.sleep(0.02)
    app.processEvents()
    assert not envios.is_running, "a operação não terminou no tempo esperado"


def main() -> int:
    main_window_module.QSettings = _FakeSettings  # type: ignore[assignment]
    envios_tab_module.QSettings = _FakeSettings  # type: ignore[assignment]

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        contatos, pasta = _fixtures(base)

        app = QApplication([])
        app.setStyle("Fusion")
        app.setFont(QFont(APP_FONT, 9))
        app.setStyleSheet(build_stylesheet())

        window = MainWindow()
        window.show()
        app.processEvents()

        assert window._tabs.count() == 2, window._tabs.count()
        envios = window._envios_tab

        envios._segmented.set_current("transportador")
        envios._contacts_selector.set_path(contatos)
        envios._folder_selector.set_path(pasta)
        app.processEvents()

        # ---- modelos separados por tipo de relatório -------------------
        assunto_transportador = envios._subject.text()
        corpo_transportador = envios._body.toHtml()
        envios._subject.setText("{transportadora} - teste de persistência")
        envios._body.setPlainText("Corpo personalizado para {transportadora}")
        envios._segmented.set_current("motorista")
        assert "INS do Motorista" in envios._subject.text(), envios._subject.text()
        envios._segmented.set_current("transportador")
        assert (
            envios._subject.text() == "{transportadora} - teste de persistência"
        ), envios._subject.text()
        assert "Corpo personalizado" in envios._body.toPlainText()
        envios._subject.setText(assunto_transportador)
        envios._body.setHtml(corpo_transportador)

        # ---- lista manual de cópias -----------------------------------
        envios._copy_input.setText(
            "copia@gruposc.com.br; qualidade@gruposc.com.br"
        )
        envios._add_copy_emails()
        assert envios.copy_emails() == [
            "copia@gruposc.com.br",
            "qualidade@gruposc.com.br",
        ], envios.copy_emails()
        assert envios._copy_list.count() == 2
        assert not envios._copy_list.alternatingRowColors(), (
            "a lista de cópias não deve usar linhas alternadas do tema do Windows"
        )

        # ---- persistência da lista de cópias --------------------------
        envios.save_settings()
        envios._copy_list.clear()
        envios._restore_settings()
        assert envios._copy_list.count() == 2, envios._copy_list.count()
        assert "2 endereço" in envios._copy_hint.text(), (
            envios._copy_hint.text()
        )

        plano = montar_plano(
            "transportador",
            contatos,
            pasta,
            copia_manual=["copia@gruposc.com.br"],
            assunto=envios._subject.text(),
            corpo=envios._body.toHtml(),
        )
        assert len(plano.grupos) == 3, len(plano.grupos)

        dialog = EnviosConfirmDialog(plano, debug=False)
        assert dialog.table.rowCount() == 3, dialog.table.rowCount()
        assert dialog.selected_keys() == ["alfa", "beta"], dialog.selected_keys()
        assert dialog.confirm_button.text().startswith("Confirmar envio")
        assert dialog._preview_subject.text().startswith("Alfa"), (
            dialog._preview_subject.text()
        )
        assert "Alfa" in dialog._preview_body.text()
        assert "copia@gruposc.com.br" in dialog._preview_recipients.text(), (
            dialog._preview_recipients.text()
        )
        dialog.table.selectRow(1)
        assert dialog._preview_subject.text().startswith("Beta"), (
            dialog._preview_subject.text()
        )
        dialog.table.selectRow(0)

        # ---- proporções, rolagem e acessibilidade do diálogo -----------
        dialog.show()
        app.processEvents()
        dialog.resize(760, 480)
        app.processEvents()
        assert dialog.minimumWidth() <= 760, dialog.minimumWidth()
        assert dialog.minimumHeight() <= 480, dialog.minimumHeight()
        assert getattr(dialog, "_scroll", None) is not None
        assert dialog._scroll.widgetResizable()
        assert dialog._scroll.verticalScrollBar().maximum() > 0, (
            "o conteúdo precisa rolar em telas baixas"
        )
        assert dialog.confirm_button.isVisible()
        assert dialog.confirm_button.geometry().bottom() <= dialog.height(), (
            dialog.confirm_button.geometry(),
            dialog.height(),
        )
        assert dialog.confirm_button.accessibleName()
        assert dialog.table.accessibleName()
        assert dialog.select_all.accessibleName()
        assert dialog._checks[0].accessibleName()
        assert dialog._checks[0].minimumWidth() >= 24
        assert dialog._checks[0].minimumHeight() >= 24
        assert dialog.select_all.minimumWidth() >= 24
        assert dialog.select_all.minimumHeight() >= 24
        assert envios._contacts_selector._clear_button.width() >= 24
        assert envios._contacts_selector._clear_button.height() >= 24

        # ---- ordem de foco lógica --------------------------------------
        dialog.select_all.setFocus()
        QTest.keyClick(dialog.select_all, Qt.Key.Key_Tab)
        assert dialog.table.hasFocus(), "Tab deve ir do topo para a tabela"
        QTest.keyClick(dialog.table, Qt.Key.Key_Tab)
        assert dialog._scroll.hasFocus(), "Tab deve sair da tabela para a prévia"
        QTest.keyClick(dialog._scroll, Qt.Key.Key_Tab)
        assert dialog.cancel_button.hasFocus(), "Tab deve chegar ao Cancelar"
        QTest.keyClick(dialog.cancel_button, Qt.Key.Key_Tab)
        assert dialog.confirm_button.hasFocus(), "Tab deve chegar ao Confirmar"

        # ---- operação por teclado na tabela ----------------------------
        dialog.table.setFocus()
        dialog.table.selectRow(0)
        assert dialog._checks[0].isChecked()
        QTest.keyClick(dialog.table, Qt.Key.Key_Space)
        assert not dialog._checks[0].isChecked()
        assert "alfa" not in dialog.selected_keys(), dialog.selected_keys()
        QTest.keyClick(dialog.table, Qt.Key.Key_Space)
        assert dialog._checks[0].isChecked()
        assert "alfa" in dialog.selected_keys(), dialog.selected_keys()

        capturas = Path("_saida_teste")
        capturas.mkdir(exist_ok=True)
        dialog.grab().save(str(capturas / "envios_dialogo_baixo.png"))
        dialog.close()

        dialog._checks[0].setChecked(False)
        assert dialog.selected_keys() == ["beta"], dialog.selected_keys()
        assert "1" in dialog.confirm_button.text()
        dialog.select_all.setChecked(True)
        assert dialog.selected_keys() == ["alfa", "beta"], dialog.selected_keys()
        dialog.select_all.setChecked(False)
        assert dialog.selected_keys() == [], dialog.selected_keys()
        dialog.select_all.setChecked(True)
        assert dialog.selected_keys() == ["alfa", "beta"], dialog.selected_keys()
        dialog.close()

        debug_dialog = EnviosConfirmDialog(plano, debug=True)
        assert debug_dialog.confirm_button.isHidden()
        assert debug_dialog.cancel_button.text() == "Fechar"
        assert not debug_dialog._checks[0].isEnabled()
        debug_dialog.close()

        envios._debug_check.setChecked(True)
        assert "Validar" in envios._prepare_button.text()
        envios._debug_check.setChecked(False)
        assert "Preparar" in envios._prepare_button.text()

        # ---- fluxo real sem Outlook: thread de plano + confirmação -----
        enviados: list[str] = []
        envios._start_send = lambda plano, chaves: enviados.extend(chaves)
        envios._dialog_factory = _FakeDialog

        envios._debug_check.setChecked(True)
        envios._prepare_button.click()
        _wait(envios, app)
        assert envios.plano is not None
        assert len(envios.plano.grupos) == 3, len(envios.plano.grupos)
        assert not enviados, enviados
        assert any(
            registro["categoria"] == "validado"
            and registro["transportadora"] == "Alfa"
            for registro in envios._log_records
        ), envios._log_records
        assert any(
            registro["categoria"] == "nao_encontrado"
            and registro["transportadora"] == "Gama"
            for registro in envios._log_records
        ), envios._log_records

        envios._debug_check.setChecked(False)
        _FakeDialog.aceitar = True
        enviados.clear()
        envios._prepare_button.click()
        _wait(envios, app)
        assert enviados == ["alfa", "beta"], enviados

        window._tabs.setCurrentIndex(1)
        output = Path("_saida_teste")
        output.mkdir(exist_ok=True)
        for indice, nome in (
            (0, "envios"),
            (1, "corpo"),
            (2, "copia"),
            (3, "log"),
        ):
            envios._tabs.setCurrentIndex(indice)
            app.processEvents()
            window.grab().save(str(output / f"envios_{nome}.png"))
        envios._tabs.setCurrentIndex(0)
        app.processEvents()

        window._tabs.setCurrentIndex(0)
        app.processEvents()
        window.grab().save(str(output / "geracao.png"))
        window._tabs.setCurrentIndex(1)
        app.processEvents()

        if envios.plano is not None:
            dialogo = EnviosConfirmDialog(envios.plano, debug=False)
            dialogo.show()
            app.processEvents()
            dialogo.grab().save(str(output / "envios_dialogo.png"))
            dialogo.close()

            dialogo_debug = EnviosConfirmDialog(envios.plano, debug=True)
            dialogo_debug.show()
            app.processEvents()
            dialogo_debug.grab().save(
                str(output / "envios_dialogo_debug.png")
            )
            dialogo_debug.close()
        print("capturas:", (output.resolve()))

        window.close()
        app.processEvents()
        print("OK: aba Envios montada e tabela de confirmação validada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
