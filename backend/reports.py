"""Definições dos tipos de relatório INS suportados pela aplicação.

Cada tipo de relatório descreve como a planilha de origem deve ser lida e
como o template de dashboard deve ser preenchido.  Nenhum caminho de arquivo
é fixado aqui: todos vêm da interface gráfica.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Caracteres proibidos em nomes de arquivo no Windows.
_INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_MAX_NAME_LENGTH = 90


def sanitize_filename(name: str) -> str:
    """Converte um nome de grupo em um nome de arquivo seguro no Windows."""
    clean = _INVALID_FILENAME_CHARS.sub("_", str(name)).strip().rstrip(".")
    clean = re.sub(r"\s+", " ", clean)
    if not clean:
        clean = "SEM_NOME"
    return clean[:_MAX_NAME_LENGTH]


@dataclass(frozen=True, slots=True)
class ReportType:
    """Configuração imutável de um tipo de relatório."""

    key: str
    label: str
    short_label: str
    description: str
    source_sheet: str
    template_sheet: str
    template_table: str
    group_column: str
    output_prefix: str
    keep_columns: tuple[str, ...] = ()
    drop_columns: tuple[str, ...] = ()
    uppercase_group_values: bool = False
    reuse_template: bool = False

    @property
    def uses_keep_list(self) -> bool:
        return bool(self.keep_columns)

    def output_filename(self, group_name: str) -> str:
        return f"{self.output_prefix} - {sanitize_filename(group_name)}.xlsx"


MOTORISTA = ReportType(
    key="motorista",
    label="INS do Motorista",
    short_label="Motorista",
    description=(
        "Gera um dashboard por apelido de motorista a partir da aba INS da "
        "planilha de origem."
    ),
    source_sheet="INS",
    template_sheet="INS",
    template_table="INS",
    group_column="Apelido",
    output_prefix="INS do Motorista",
    keep_columns=(
        "Mês",
        "Rota/Roteiro",
        "Tipo_Operação",
        "Apelido",
        "CD",
        "Embarcada",
        "Entrega Meta",
        "Ocorrencias",
        "Ocorrencias_Validas",
        "Viagens",
        "Logins",
        "Volumes",
        "Volumetria",
        "Transit_Time",
    ),
)

TRANSPORTADOR = ReportType(
    key="transportador",
    label="INS do Transportador",
    short_label="Transportador",
    description=(
        "Gera um dashboard por transportadora a partir da aba INS da planilha "
        "de origem, removendo as colunas que não fazem parte do relatório."
    ),
    source_sheet="INS",
    template_sheet="Dados",
    template_table="Tabela3",
    group_column="TRANSPORTADOR",
    output_prefix="INS do Transportador",
    uppercase_group_values=True,
    # Template com Data Model + tabelas dinâmicas OLAP: o template é aberto
    # uma única vez e cada grupo é salvo com SaveCopyAs, mantendo o modelo
    # quente entre os grupos (pivôs e formas do Resumo permanecem intactos).
    reuse_template=True,
    drop_columns=(
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
        "Acidente",
    ),
)

REPORT_TYPES: dict[str, ReportType] = {
    MOTORISTA.key: MOTORISTA,
    TRANSPORTADOR.key: TRANSPORTADOR,
}


def get_report_type(key: str) -> ReportType:
    """Retorna o tipo de relatório pelo identificador.

    Levanta ``KeyError`` com mensagem amigável se o identificador não existir.
    """
    try:
        return REPORT_TYPES[key]
    except KeyError:
        valid = ", ".join(sorted(REPORT_TYPES))
        raise KeyError(
            f"Tipo de relatório desconhecido: {key!r}. Valores válidos: {valid}."
        ) from None
