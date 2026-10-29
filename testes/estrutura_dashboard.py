"""Confere a integridade estrutural dos dashboards gerados.

Compara o pacote OOXML de cada dashboard com o template: tabelas dinâmicas,
caches, Data Model, formas do ``Resumo``, gráficos e imagens.  Uma diferença
aqui significa que o dashboard perdeu elementos visuais, mesmo que os valores
das células estejam corretos.

Uso::

    python -m testes.estrutura_dashboard ^
        --template "C:\\INS\\Template - Transportador.xlsx" ^
        --pasta "C:\\...\\saida"
"""

from __future__ import annotations

import argparse
import re
import sys
import zipfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

PARTES = {
    "tabelas_dinamicas": re.compile(r"xl/pivotTables/pivotTable\d+\.xml$"),
    "caches": re.compile(r"xl/pivotCache/pivotCacheDefinition\d+\.xml$"),
    "modelo": re.compile(r"xl/model/item\.data$"),
    "graficos": re.compile(r"xl/charts/chart\d+\.xml$"),
    "desenhos": re.compile(r"xl/drawings/drawing\d+\.xml$"),
    "imagens": re.compile(r"xl/media/[^/]+$"),
}

_FORMAS = re.compile(r"<xdr:cNvPr\b[^>]*\bname=\"([^\"]*)\"")
_ANCORAS = re.compile(r"<xdr:(?:twoCellAnchor|oneCellAnchor|absoluteAnchor)\b")


@dataclass(frozen=True)
class Inventario:
    partes: dict[str, int]
    formas: Counter[str]
    ancoras: dict[str, int]
    tamanho_mb: float
    calculo: str = "auto"

    @property
    def total_formas(self) -> int:
        return sum(self.formas.values())


@dataclass
class Diferenca:
    arquivo: str
    problemas: list[str] = field(default_factory=list)


def _modo_calculo(pacote: zipfile.ZipFile) -> str:
    """Modo gravado em <calcPr>. ``manual`` deixa os campos TxLink em branco."""
    try:
        xml = pacote.read("xl/workbook.xml").decode("utf-8", "ignore")
    except KeyError:
        return "auto"
    trecho = re.search(r"<calcPr[^>]*/>", xml)
    if not trecho:
        return "auto"
    modo = re.search(r'calcMode="([^"]+)"', trecho.group(0))
    return modo.group(1) if modo else "auto"


def inventariar(caminho: Path) -> Inventario:
    caminho = Path(caminho)
    with zipfile.ZipFile(caminho) as pacote:
        nomes = pacote.namelist()
        contagem = {
            chave: len([n for n in nomes if padrao.match(n)])
            for chave, padrao in PARTES.items()
        }
        formas: Counter[str] = Counter()
        ancoras: Counter[str] = Counter()
        for nome in nomes:
            if not PARTES["desenhos"].match(nome):
                continue
            xml = pacote.read(nome).decode("utf-8", "ignore")
            formas.update(_FORMAS.findall(xml))
            ancoras.update(_ANCORAS.findall(xml))
        calculo = _modo_calculo(pacote)
    return Inventario(
        partes=contagem,
        formas=formas,
        ancoras=dict(ancoras),
        tamanho_mb=round(caminho.stat().st_size / 1024 / 1024, 3),
        calculo=calculo,
    )


def comparar(referencia: Inventario, candidato: Inventario) -> list[str]:
    problemas: list[str] = []

    for chave in PARTES:
        esperado = referencia.partes[chave]
        obtido = candidato.partes[chave]
        if esperado != obtido:
            problemas.append(f"{chave}: template={esperado}, gerado={obtido}")

    faltando = referencia.formas - candidato.formas
    extras = candidato.formas - referencia.formas
    if faltando:
        nomes = ", ".join(sorted(faltando)[:5])
        problemas.append(
            f"formas ausentes: {sum(faltando.values())} ({nomes}...)"
        )
    if extras:
        nomes = ", ".join(sorted(extras)[:5])
        problemas.append(f"formas a mais: {sum(extras.values())} ({nomes}...)")

    if referencia.ancoras != candidato.ancoras:
        problemas.append(
            f"âncoras do desenho: template={referencia.ancoras}, "
            f"gerado={candidato.ancoras}"
        )

    if candidato.calculo == "manual":
        problemas.append(
            "modo de cálculo: gerado=manual (os cards TxLink ficam em branco "
            "até o usuário forçar um recálculo)"
        )
    return problemas


def verificar_pasta(template: Path, pasta: Path) -> list[Diferenca]:
    referencia = inventariar(template)
    saidas = sorted(Path(pasta).glob("INS do Transportador - *.xlsx"))
    resultados: list[Diferenca] = []
    for saida in saidas:
        problemas = comparar(referencia, inventariar(saida))
        if problemas:
            resultados.append(Diferenca(saida.name, problemas))
    return resultados


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", required=True, type=Path)
    parser.add_argument("--pasta", required=True, type=Path)
    args = parser.parse_args(argv)

    referencia = inventariar(args.template)
    print(
        f"template: {args.template.name} ({referencia.tamanho_mb} MB) | "
        f"pivôs={referencia.partes['tabelas_dinamicas']} "
        f"caches={referencia.partes['caches']} "
        f"modelo={referencia.partes['modelo']} "
        f"formas={referencia.total_formas} "
        f"gráficos={referencia.partes['graficos']} "
        f"imagens={referencia.partes['imagens']} "
        f"cálculo={referencia.calculo}"
    )

    saidas = sorted(args.pasta.glob("INS do Transportador - *.xlsx"))
    if not saidas:
        print(f"nenhum dashboard encontrado em {args.pasta}", file=sys.stderr)
        return 1

    divergentes = 0
    for saida in saidas:
        inventario = inventariar(saida)
        problemas = comparar(referencia, inventario)
        if problemas:
            divergentes += 1
            print(f"[DIVERGE] {saida.name}")
            for problema in problemas:
                print(f"    {problema}")
        else:
            print(
                f"[ok] {saida.name} ({inventario.tamanho_mb} MB, "
                f"{inventario.total_formas} formas)"
            )

    print(
        f"\n{len(saidas) - divergentes}/{len(saidas)} dashboards "
        f"estruturalmente idênticos ao template."
    )
    return 1 if divergentes else 0


if __name__ == "__main__":
    raise SystemExit(main())
