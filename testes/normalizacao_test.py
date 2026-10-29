"""Testes do Data Wrangling aplicado à coluna de agrupamento.

Valida que a coluna ``Apelido`` do INS do Motorista é normalizada
(``strip()`` + espaços colapsados + MAIÚSCULAS) **antes** de separar os
grupos, evitando dashboards duplicados para o mesmo motorista.

Execução (a partir de ins_dashboard_app)::

    python -m unittest testes.normalizacao_test -v
"""

from __future__ import annotations

import unittest

import pandas as pd

from backend.processor import DashboardProcessor
from backend.reports import MOTORISTA, TRANSPORTADOR


def _linha(apelido: object, mes: str = "Jan") -> dict[str, object]:
    """Monta uma linha mínima com todas as colunas do relatório Motorista."""
    base = {coluna: 1 for coluna in MOTORISTA.keep_columns}
    base.update({"Mês": mes, "Rota/Roteiro": "R1", "Tipo_Operação": "Entrega"})
    base["Apelido"] = apelido
    return base


class DataWranglingMotoristaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.processor = DashboardProcessor()

    def test_apelido_e_normalizado_antes_do_agrupamento(self) -> None:
        dataframe = pd.DataFrame(
            [
                _linha("  joão "),
                _linha("JOÃO"),
                _linha("João"),
                _linha("maria"),
                _linha("  MARIA  "),
            ]
        )

        grupos = self.processor._split_groups(dataframe, MOTORISTA)

        self.assertEqual([nome for nome, _ in grupos], ["JOÃO", "MARIA"])
        esperado = {"JOÃO": 3, "MARIA": 2}
        for nome, dados in grupos:
            self.assertEqual(len(dados), esperado[nome])
            # A coluna gravada no dashboard também precisa sair padronizada.
            self.assertEqual(set(dados["Apelido"]), {nome})

    def test_espacos_duplos_e_quebras_de_linha_sao_colapsados(self) -> None:
        dataframe = pd.DataFrame(
            [_linha("ANA\t PAULA"), _linha("ana  paula")]
        )

        grupos = self.processor._split_groups(dataframe, MOTORISTA)

        self.assertEqual([nome for nome, _ in grupos], ["ANA PAULA"])
        self.assertEqual(len(grupos[0][1]), 2)

    def test_linhas_sem_apelido_sao_ignoradas(self) -> None:
        dataframe = pd.DataFrame([_linha("João"), _linha(None)])

        grupos = self.processor._split_groups(dataframe, MOTORISTA)

        self.assertEqual([nome for nome, _ in grupos], ["JOÃO"])
        self.assertEqual(len(grupos[0][1]), 1)

    def test_apelido_apenas_com_espacos_recebe_rotulo(self) -> None:
        dataframe = pd.DataFrame([_linha("   ")])

        grupos = self.processor._split_groups(dataframe, MOTORISTA)

        self.assertEqual([nome for nome, _ in grupos], ["SEM IDENTIFICACAO"])
        self.assertEqual(grupos[0][1]["Apelido"].iloc[0], "SEM IDENTIFICACAO")

    def test_transportador_tambem_recebe_strip_sem_perder_caixa(self) -> None:
        # O Transportador usa MAIÚSCULAS; o teste garante que o strip também
        # vale para ele e que não sobram grupos duplicados por espaço.
        dataframe = pd.DataFrame(
            [
                {"TRANSPORTADOR": "  Alfa ", "Mês": "Jan", "Viagens": 1},
                {"TRANSPORTADOR": "ALFA", "Mês": "Fev", "Viagens": 2},
            ]
        )

        grupos = self.processor._split_groups(dataframe, TRANSPORTADOR)

        self.assertEqual([nome for nome, _ in grupos], ["ALFA"])
        self.assertEqual(len(grupos[0][1]), 2)


if __name__ == "__main__":
    unittest.main()
