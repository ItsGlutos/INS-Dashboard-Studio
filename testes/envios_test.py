"""Testes da lógica de envio dos relatórios INS.

Execução (a partir de ``ins_dashboard_app``)::

    python -m unittest testes.envios_test -v

Os testes não abrem o Outlook: o envio é validado com um remetente falso.
"""

from __future__ import annotations

import os
import tempfile
import time
import unittest
from pathlib import Path

import pandas as pd

from backend.envios import (
    DEFAULT_ASSUNTOS,
    DEFAULT_CORPOS,
    EnvioError,
    GrupoEnvio,
    dividir_emails,
    enviar_plano,
    ler_contatos,
    localizar_arquivos,
    montar_plano,
    normalizar_chave,
    validar_email,
)


class _FakeSender:
    """Remetente falso que registra os grupos e simula falhas."""

    def __init__(self, falhar_em: set[str] | None = None) -> None:
        self.enviados: list[GrupoEnvio] = []
        self.falhar_em = falhar_em or set()
        self.fechado = False

    def enviar(self, grupo: GrupoEnvio) -> None:
        if grupo.chave in self.falhar_em:
            raise RuntimeError("falha simulada no Outlook")
        self.enviados.append(grupo)

    def fechar(self) -> None:
        self.fechado = True


class _FakeSenderFactory:
    def __init__(self, sender: _FakeSender) -> None:
        self.sender = sender

    def __call__(self) -> _FakeSender:
        return self.sender


def _criar_contatos(caminho: Path, linhas: list[dict[str, str]]) -> None:
    """Cria a planilha de contatos usada como dicionário de envios."""
    with pd.ExcelWriter(caminho) as writer:
        pd.DataFrame(linhas).to_excel(writer, sheet_name="Contatos", index=False)


def _criar_arquivo(pasta: Path, nome: str, idade_segundos: float = 0) -> Path:
    caminho = pasta / nome
    caminho.write_bytes(b"conteudo")
    if idade_segundos:
        momento = time.time() - idade_segundos
        os.utime(caminho, (momento, momento))
    return caminho


class NormalizacaoTests(unittest.TestCase):
    def test_normaliza_acentos_caixa_e_espacos(self) -> None:
        self.assertEqual(normalizar_chave("  Ála  Uber "), "ala uber")
        self.assertEqual(normalizar_chave("5S   TRANSPORTES"), "5s transportes")

    def test_valida_email(self) -> None:
        self.assertTrue(validar_email("farmaceutico@medlog.log.br"))
        self.assertFalse(validar_email("sem-arroba"))
        self.assertFalse(validar_email("a@b"))
        self.assertFalse(validar_email("a b@c.com"))
        self.assertFalse(validar_email("a@b..com"))
        self.assertFalse(validar_email(".a@b.com"))
        self.assertFalse(validar_email("a.@b.com"))

    def test_divide_lista_de_emails(self) -> None:
        emails = dividir_emails(
            "a@b.com; c@d.com,\n e@f.com  a@b.com"
        )
        self.assertEqual(emails, ["a@b.com", "c@d.com", "e@f.com"])


class LeituraContatosTests(unittest.TestCase):
    def test_le_e_agrupa_contatos_por_transportadora(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            caminho = Path(tmp) / "contatos.xlsx"
            _criar_contatos(
                caminho,
                [
                    {"Transportadora": "Alfa", "E-mail": "a@alfa.com"},
                    {"Transportadora": " alfa ", "E-mail": "b@alfa.com"},
                    {"Transportadora": "Alfa", "E-mail": "a@alfa.com"},
                    {"Transportadora": "Beta", "E-mail": ""},
                ],
            )
            contatos = ler_contatos(caminho)
            self.assertIn("alfa", contatos)
            self.assertEqual(
                contatos["alfa"].emails, ("a@alfa.com", "b@alfa.com")
            )
            self.assertEqual(contatos["beta"].emails, ())

    def test_planilha_sem_colunas_obrigatorias_falha_com_mensagem(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            caminho = Path(tmp) / "contatos.xlsx"
            _criar_contatos(caminho, [{"Nome": "Alfa", "Email": "a@alfa.com"}])
            with self.assertRaises(EnvioError) as contexto:
                ler_contatos(caminho)
            self.assertIn("Transportadora", str(contexto.exception))
            self.assertIn("E-mail", str(contexto.exception))


class LocalizacaoArquivosTests(unittest.TestCase):
    def test_encontra_somente_arquivos_do_tipo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pasta = Path(tmp)
            _criar_arquivo(pasta, "INS do Transportador - Alfa.xlsx")
            _criar_arquivo(pasta, "INS do Motorista - Beta.xlsx")
            _criar_arquivo(pasta, "outro.xlsx")
            _criar_arquivo(pasta, "~$INS do Transportador - Alfa.xlsx")

            arquivos = localizar_arquivos(pasta, "transportador")
            self.assertEqual(
                [arquivo.nome_transportador for arquivo in arquivos], ["Alfa"]
            )

    def test_pasta_inexistente_falha_com_mensagem(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(EnvioError) as contexto:
                localizar_arquivos(Path(tmp) / "nao_existe", "motorista")
            self.assertIn("não encontrada", str(contexto.exception))


class PlanoTests(unittest.TestCase):
    def _base(self, tmp: Path) -> tuple[Path, Path]:
        pasta = tmp / "arquivos"
        pasta.mkdir()
        contatos = tmp / "contatos.xlsx"
        _criar_contatos(
            contatos,
            [
                {"Transportadora": "Alfa", "E-mail": "a@alfa.com;b@alfa.com"},
                {"Transportadora": "Beta", "E-mail": ""},
                {"Transportadora": "Delta", "E-mail": "invalido"},
                {
                    "Transportadora": "Épsilon",
                    "E-mail": "e@epsilon.com; outro-invalido",
                },
            ],
        )
        _criar_arquivo(pasta, "INS do Transportador - Alfa.xlsx")
        _criar_arquivo(pasta, "INS do Transportador - Beta.xlsx")
        _criar_arquivo(pasta, "INS do Transportador - Delta.xlsx")
        _criar_arquivo(pasta, "INS do Transportador - Epsilon.xlsx")
        _criar_arquivo(pasta, "INS do Transportador - Gama.xlsx")
        return contatos, pasta

    def test_monta_plano_com_status_por_transportadora(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            contatos, pasta = self._base(Path(tmp))
            plano = montar_plano(
                "transportador",
                contatos,
                pasta,
                copia_manual=["copia@gruposc.com.br"],
                assunto="{transportadora} - INS",
                corpo="Olá, {transportadora}!",
            )

            por_chave = {grupo.chave: grupo for grupo in plano.grupos}
            self.assertEqual(por_chave["alfa"].status, "pronto")
            self.assertEqual(por_chave["alfa"].para, ("a@alfa.com", "b@alfa.com"))
            self.assertEqual(
                por_chave["alfa"].copia, ("copia@gruposc.com.br",)
            )
            self.assertEqual(por_chave["alfa"].assunto, "Alfa - INS")
            self.assertEqual(por_chave["alfa"].corpo, "Olá, Alfa!")
            self.assertEqual(por_chave["beta"].status, "sem_email")
            self.assertEqual(por_chave["delta"].status, "email_invalido")
            self.assertEqual(por_chave["gama"].status, "sem_contato")
            self.assertEqual(por_chave["epsilon"].status, "pronto")
            self.assertEqual(
                por_chave["epsilon"].emails_invalidos, ("outro-invalido",)
            )

    def test_escolhe_arquivo_mais_recente_quando_ha_duplicados(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            contatos, pasta = self._base(Path(tmp))
            antigo = _criar_arquivo(
                pasta, "INS do Transportador - Alfa.xlsx", idade_segundos=600
            )
            novo = _criar_arquivo(
                pasta, "INS do Transportador - Álfa.xlsx", idade_segundos=0
            )
            plano = montar_plano("transportador", contatos, pasta)
            alfa = [grupo for grupo in plano.grupos if grupo.chave == "alfa"]
            self.assertEqual(len(alfa), 1)
            self.assertEqual(alfa[0].arquivo, novo)
            self.assertTrue(any(str(antigo) in aviso for aviso in plano.avisos))

    def test_emails_de_copia_invalidos_geram_aviso(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            contatos, pasta = self._base(Path(tmp))
            plano = montar_plano(
                "transportador",
                contatos,
                pasta,
                copia_manual=["ok@gruposc.com.br", "invalido"],
            )
            self.assertTrue(plano.avisos)
            self.assertTrue(
                any("invalido" in aviso.lower() for aviso in plano.avisos)
            )

    def test_padroes_por_tipo_contem_marcador(self) -> None:
        for chave in ("motorista", "transportador"):
            self.assertIn("{transportadora}", DEFAULT_ASSUNTOS[chave])
            self.assertIn("{transportadora}", DEFAULT_CORPOS[chave])


class EnvioTests(unittest.TestCase):
    def _plano(self, tmp: Path):
        contatos = tmp / "contatos.xlsx"
        pasta = tmp / "arquivos"
        pasta.mkdir()
        _criar_contatos(
            contatos,
            [
                {"Transportadora": "Alfa", "E-mail": "a@alfa.com"},
                {"Transportadora": "Beta", "E-mail": "b@beta.com"},
                {"Transportadora": "Gama", "E-mail": ""},
            ],
        )
        for nome in ("Alfa", "Beta", "Gama"):
            _criar_arquivo(pasta, f"INS do Transportador - {nome}.xlsx")
        return montar_plano(
            "transportador", contatos, pasta, corpo="Olá {transportadora}"
        )

    def test_envia_selecionados_e_continua_apos_falha(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plano = self._plano(Path(tmp))
            sender = _FakeSender(falhar_em={"beta"})
            logs: list[tuple[str, str]] = []
            resultado = enviar_plano(
                plano,
                chaves=[grupo.chave for grupo in plano.grupos],
                sender_factory=_FakeSenderFactory(sender),
                on_log=lambda mensagem, nivel: logs.append((mensagem, nivel)),
            )

            self.assertEqual([grupo.chave for grupo in resultado.enviados], ["alfa"])
            self.assertEqual([grupo.chave for grupo in resultado.falhos], ["beta"])
            self.assertEqual(
                [grupo.chave for grupo in resultado.nao_encontrados], ["gama"]
            )
            self.assertTrue(sender.fechado)
            self.assertTrue(
                any("falha simulada" in mensagem for mensagem, _ in logs)
            )

    def test_nao_envia_grupo_sem_email(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plano = self._plano(Path(tmp))
            sender = _FakeSender()
            resultado = enviar_plano(
                plano, chaves=["gama"], sender_factory=_FakeSenderFactory(sender)
            )
            self.assertEqual(resultado.enviados, [])
            self.assertEqual(
                [grupo.chave for grupo in resultado.nao_encontrados], ["gama"]
            )
            self.assertEqual(sender.enviados, [])

    def test_cancelamento_interrompe_os_envios_restantes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plano = self._plano(Path(tmp))
            sender = _FakeSender()
            resultado = enviar_plano(
                plano,
                chaves=["alfa", "beta"],
                sender_factory=_FakeSenderFactory(sender),
                should_cancel=lambda: bool(sender.enviados),
            )
            self.assertTrue(resultado.cancelado)
            self.assertEqual([grupo.chave for grupo in resultado.enviados], ["alfa"])
            self.assertEqual(
                [grupo.chave for grupo in resultado.ignorados], ["beta"]
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
