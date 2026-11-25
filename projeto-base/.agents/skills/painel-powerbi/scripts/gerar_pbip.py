"""Gera um projeto do Power BI Desktop (.pbip) a partir de uma especificação em JSON.

O projeto é gerado, nunca editado à mão: para mudar o painel, mude a especificação e
gere de novo. A mesma especificação produz sempre os mesmos arquivos, com os mesmos
identificadores, o que permite versionar o painel no Git e comparar as mudanças.

Uso, a partir da pasta do projeto:

    python .claude/skills/painel-powerbi/scripts/gerar_pbip.py powerbi/painel.json
    python .claude/skills/painel-powerbi/scripts/gerar_pbip.py powerbi/painel.json --force
    python .claude/skills/painel-powerbi/scripts/gerar_pbip.py powerbi/painel.json --dry-run

Usa só a biblioteca padrão do Python 3.9 ou mais novo. A opção --validar-esquemas
confere os arquivos com os esquemas oficiais da Microsoft; ela precisa do pacote
jsonschema e de internet na primeira vez.
"""
from __future__ import annotations

import argparse
import csv
import difflib
import hashlib
import json
import platform
import re
import shutil
import sys
import tempfile
import uuid
from pathlib import Path

NAMESPACE = uuid.UUID("5b0c7a52-3f0e-4d4e-9a61-2f6f3c1d8e47")
FABRIC = "https://developer.microsoft.com/json-schemas/fabric/"
ITEM = FABRIC + "item/"
PAGE_WIDTH, PAGE_HEIGHT = 1280, 720
HEADER_BOTTOM = 96
NOTE_TOP = PAGE_HEIGHT - 56
TEXT_COLOR = "#18354A"
SOFT_COLOR = "#526574"
PARAMETER = "CaminhoCsv"
IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
TMDL_PLAIN = re.compile(r"^[^\W\d]\w*$")
TYPES = {"texto": "string", "inteiro": "int64", "decimal": "double"}
VISUAL_TYPES = {
    "cartao": "card",
    "barras": "clusteredBarChart",
    "colunas": "clusteredColumnChart",
    "linhas": "lineChart",
    "dispersao": "scatterChart",
    "tabela": "tableEx",
    "segmentacao": "slicer",
    "texto": "textbox",
}
# Campos obrigatórios e opcionais de cada tipo de visual na especificação.
VISUAL_FIELDS = {
    "cartao": ({"medida"}, set()),
    "barras": ({"categoria", "valor"}, {"serie", "top", "ordenar"}),
    "colunas": ({"categoria", "valor"}, {"serie", "top", "ordenar"}),
    "linhas": ({"categoria", "valor"}, {"serie"}),
    "dispersao": ({"detalhe", "x", "y"}, {"tamanho", "legenda", "escala_log"}),
    "tabela": ({"campos"}, set()),
    "segmentacao": ({"campo"}, set()),
    "texto": ({"texto"}, {"tamanho_fonte"}),
}
COMMON_FIELDS = {"tipo", "titulo", "subtitulo", "posicao"}


class SpecError(ValueError):
    """Problemas na especificação, explicados em português para o aluno."""

    def __init__(self, problems):
        self.problems = list(problems)
        super().__init__("\n".join("- " + p for p in self.problems))


# ---------------------------------------------------------------------------
# Leitura e conferência da especificação
# ---------------------------------------------------------------------------

def read_csv(path, delimiter):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle, delimiter=delimiter)
        header = next(reader, None)
        if header is None:
            raise SpecError(["O CSV está vazio: " + str(path)])
        return header, list(reader)


def parse_number(text, kind):
    if text == "":
        return None
    if kind == "inteiro":
        if not re.fullmatch(r"-?\d+", text):
            raise ValueError(text)
        return int(text)
    if not re.fullmatch(r"-?\d+(\.\d+)?", text):
        raise ValueError(text)
    return float(text)


def suggest(name, options):
    close = difflib.get_close_matches(name, list(options), n=1)
    return f" Você quis dizer '{close[0]}'?" if close else ""


def load_spec(spec_path):
    spec_path = Path(spec_path).resolve()
    try:
        spec = json.loads(spec_path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        raise SpecError([f"Não encontrei a especificação {spec_path}."]) from None
    except json.JSONDecodeError as error:
        raise SpecError([f"A especificação não é um JSON válido (linha {error.lineno}, "
                         f"coluna {error.colno}): {error.msg}."]) from None
    if not isinstance(spec, dict):
        raise SpecError(["A especificação precisa ser um objeto JSON, entre chaves."])
    return check_spec(spec, spec_path.parent)


def check_spec(spec, base_dir):
    """Confere a especificação inteira e devolve um modelo pronto para gerar.

    Junta todos os problemas antes de falhar, para o aluno corrigir de uma vez.
    """
    problems = []
    name = spec.get("nome", "")
    if not isinstance(name, str) or not IDENTIFIER.match(name):
        problems.append("'nome' precisa começar com letra e ter só letras sem acento, números e _ "
                        "(ele vira o nome do arquivo .pbip). Exemplo: PainelMunicipios.")
    table = spec.get("tabela", "")
    if not isinstance(table, str) or not IDENTIFIER.match(table):
        problems.append("'tabela' precisa começar com letra e ter só letras sem acento, números e _. "
                        "Exemplo: Municipios.")
    title = spec.get("titulo")
    if not isinstance(title, str) or not title.strip():
        problems.append("'titulo' precisa ser um texto: o título do painel.")
    delimiter = spec.get("separador", ",")
    if not isinstance(delimiter, str) or len(delimiter) != 1:
        problems.append("'separador' precisa ser um único caractere, como \",\" ou \";\".")
        delimiter = ","

    csv_path = None
    header, rows = [], []
    if not isinstance(spec.get("csv"), str):
        problems.append("'csv' precisa ser o caminho do arquivo de dados, relativo à pasta da especificação.")
    else:
        csv_path = (base_dir / spec["csv"]).resolve()
        if not csv_path.is_file():
            problems.append(f"Não encontrei o CSV {csv_path}.")
            csv_path = None
        else:
            header, rows = read_csv(csv_path, delimiter)

    columns = spec.get("colunas")
    if not isinstance(columns, dict) or not columns:
        problems.append("'colunas' precisa listar as colunas do CSV usadas no painel, com o tipo de "
                        "cada uma: \"texto\", \"inteiro\" ou \"decimal\".")
        columns = {}
    for column, kind in columns.items():
        if kind not in TYPES:
            problems.append(f"A coluna '{column}' tem tipo '{kind}'. Use \"texto\", \"inteiro\" ou \"decimal\".")
        if header and column not in header:
            problems.append(f"A coluna '{column}' não existe no CSV.{suggest(column, header)}")
        elif header and kind in ("inteiro", "decimal"):
            index = header.index(column)
            for line, row in enumerate(rows, start=2):
                value = row[index] if index < len(row) else ""
                try:
                    parse_number(value, kind)
                except ValueError:
                    problems.append(f"A coluna '{column}' foi declarada como {kind}, mas a linha {line} "
                                    f"do CSV tem '{value}'. Números usam ponto como separador decimal e "
                                    "não têm separador de milhar.")
                    break

    calculated = spec.get("colunas_calculadas", [])
    measures = spec.get("medidas", [])
    if not isinstance(calculated, list) or not isinstance(measures, list):
        problems.append("'colunas_calculadas' e 'medidas' precisam ser listas.")
        calculated, measures = [], []
    names = {}
    for column in columns:
        names[column] = "coluna"
    for item in calculated:
        if not isinstance(item, dict) or not {"nome", "dax"} <= set(item):
            problems.append("Cada coluna calculada precisa de 'nome' e 'dax'.")
            continue
        if item.get("tipo", "texto") not in TYPES:
            problems.append(f"A coluna calculada '{item['nome']}' tem tipo inválido.")
        if item["nome"] in names:
            problems.append(f"O nome '{item['nome']}' está repetido.")
        names[item["nome"]] = "coluna"
    for item in measures:
        if not isinstance(item, dict) or not {"nome", "dax"} <= set(item):
            problems.append("Cada medida precisa de 'nome' e 'dax'.")
            continue
        if item["nome"] in names:
            problems.append(f"O nome '{item['nome']}' está repetido entre colunas e medidas.")
        names[item["nome"]] = "medida"
    if not any(kind == "medida" for kind in names.values()):
        problems.append("Declare ao menos uma medida em 'medidas'. Os visuais mostram números por meio "
                        "de medidas, e não somando colunas automaticamente.")

    column_names = {n for n, k in names.items() if k == "coluna"}
    measure_names = {n for n, k in names.items() if k == "medida"}
    for item in calculated + measures:
        if isinstance(item, dict) and "dax" in item:
            problems.extend(check_dax(item["nome"], item["dax"], table, column_names, measure_names))

    pages = spec.get("paginas")
    if not isinstance(pages, list) or not pages:
        problems.append("'paginas' precisa ter ao menos uma página.")
        pages = []
    page_names = set()
    for number, page in enumerate(pages, start=1):
        problems.extend(check_page(number, page, names, page_names))

    if problems:
        raise SpecError(problems)
    return {"nome": name, "titulo": title, "tabela": table, "csv": csv_path, "separador": delimiter,
            "colunas": columns, "colunas_calculadas": calculated, "medidas": measures,
            "paginas": pages, "nomes": names, "linhas_csv": len(rows)}


def check_dax(owner, dax, table, columns, measures):
    problems = []
    if not isinstance(dax, str) or not dax.strip():
        return [f"'{owner}' precisa de uma expressão DAX."]
    if "\n" in dax:
        return [f"Escreva a expressão DAX de '{owner}' em uma única linha."]
    # Remove textos entre aspas para não confundir colchetes dentro deles.
    code = re.sub(r'"(?:[^"]|"")*"', '""', dax)
    for quoted, bare, field in re.findall(r"(?:'([^']+)'|\b([A-Za-z_][A-Za-z0-9_]*))?\[([^\]]+)\]", code):
        ref_table = quoted or bare
        if ref_table:
            if ref_table != table:
                problems.append(f"Em '{owner}', a tabela '{ref_table}' não existe. A tabela do painel "
                                f"se chama '{table}'.")
            elif field not in columns:
                problems.append(f"Em '{owner}', a coluna {table}[{field}] não existe."
                                f"{suggest(field, columns)}")
        elif field not in measures and field not in columns:
            problems.append(f"Em '{owner}', [{field}] não é medida nem coluna."
                            f"{suggest(field, measures | columns)}")
    return problems


def check_page(number, page, names, page_names):
    where = f"Página {number}"
    if not isinstance(page, dict):
        return [where + " precisa ser um objeto."]
    problems = []
    if not isinstance(page.get("nome"), str) or not page["nome"].strip():
        problems.append(where + " precisa de 'nome', o texto da aba.")
    elif page["nome"] in page_names:
        problems.append(f"Duas páginas se chamam '{page['nome']}'.")
    else:
        page_names.add(page["nome"])
        where = f"Página '{page['nome']}'"
    visuals = page.get("visuais")
    if not isinstance(visuals, list) or not visuals:
        return problems + [where + " precisa de ao menos um visual em 'visuais'."]
    boxes = []
    if page.get("titulo") or page.get("subtitulo"):
        boxes.append(("o cabeçalho da página", (0, 0, PAGE_WIDTH, HEADER_BOTTOM)))
    if page.get("nota"):
        boxes.append(("a nota de rodapé", (0, NOTE_TOP, PAGE_WIDTH, PAGE_HEIGHT - NOTE_TOP)))
    for index, item in enumerate(visuals, start=1):
        label = f"{where}, visual {index}"
        if not isinstance(item, dict):
            problems.append(label + " precisa ser um objeto.")
            continue
        kind = item.get("tipo")
        if kind not in VISUAL_TYPES:
            problems.append(f"{label}: tipo '{kind}' desconhecido. Use um destes: "
                            + ", ".join(VISUAL_TYPES) + ".")
            continue
        if item.get("titulo"):
            label = f"{where}, visual '{item['titulo']}'"
        required, optional = VISUAL_FIELDS[kind]
        missing = required - set(item)
        if missing:
            problems.append(f"{label} ({kind}) precisa de: " + ", ".join(sorted(missing)) + ".")
        extra = set(item) - required - optional - COMMON_FIELDS
        if extra:
            problems.append(f"{label} ({kind}) não usa: " + ", ".join(sorted(extra)) + ".")
        if kind not in ("texto",) and not item.get("titulo"):
            problems.append(label + " precisa de 'titulo': diga em palavras o que o visual responde.")
        problems.extend(check_fields(label, kind, item, names))
        position = item.get("posicao")
        if (not isinstance(position, list) or len(position) != 4
                or not all(isinstance(v, int) and v >= 0 for v in position)):
            problems.append(f"{label} precisa de 'posicao': [x, y, largura, altura], em pixels inteiros.")
            continue
        x, y, w, h = position
        if w < 40 or h < 30:
            problems.append(f"{label} é pequeno demais ({w} x {h}).")
        if x + w > PAGE_WIDTH or y + h > PAGE_HEIGHT:
            problems.append(f"{label} passa da borda da página, que tem {PAGE_WIDTH} x {PAGE_HEIGHT}.")
        for other, box in boxes:
            if overlaps(position, box):
                problems.append(f"{label} se sobrepõe a {other}.")
        boxes.append((f"o visual {index}", tuple(position)))
    return problems


def check_fields(label, kind, item, names):
    problems = []

    def need(key, expected):
        value = item.get(key)
        if value is None:
            return
        values = value if isinstance(value, list) else [value]
        if key in ("campos", "valor") and isinstance(value, list) and not value:
            problems.append(f"{label}: '{key}' está vazio.")
        for field in values:
            actual = names.get(field)
            if actual is None:
                problems.append(f"{label}: '{field}' não é coluna nem medida.{suggest(str(field), names)}")
            elif expected and actual != expected:
                problems.append(f"{label}: '{key}' precisa ser uma {expected}, e '{field}' é uma {actual}.")

    for key in ("categoria", "serie", "detalhe", "legenda", "campo"):
        need(key, "coluna")
    for key in ("medida", "x", "y", "tamanho"):
        need(key, "medida")
    need("valor", "medida")
    need("campos", None)
    if kind != "linhas" and isinstance(item.get("valor"), list):
        problems.append(f"{label}: em {kind}, 'valor' é uma única medida.")
    if "top" in item and (not isinstance(item["top"], int) or item["top"] < 1):
        problems.append(f"{label}: 'top' precisa ser um número inteiro positivo.")
    if item.get("ordenar", "valor") not in ("valor", "categoria"):
        problems.append(f"{label}: 'ordenar' aceita \"valor\" ou \"categoria\".")
    if "escala_log" in item and not isinstance(item["escala_log"], bool):
        problems.append(f"{label}: 'escala_log' precisa ser true ou false.")
    if kind == "texto" and not isinstance(item.get("texto"), (str, list)):
        problems.append(f"{label}: 'texto' precisa ser um texto ou uma lista de parágrafos.")
    return problems


def overlaps(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah


# ---------------------------------------------------------------------------
# Montagem dos arquivos
# ---------------------------------------------------------------------------

def tmdl_name(name):
    return name if TMDL_PLAIN.match(name) else "'" + name.replace("'", "''") + "'"


def m_string(text):
    return '"' + text.replace('"', '""') + '"'


def literal(value):
    return {"expr": {"Literal": {"Value": value}}}


def text_literal(text):
    return literal("'" + text.replace("'", "''") + "'")


class Builder:
    def __init__(self, model, lineage):
        self.model = model
        self.lineage = dict(lineage)
        self.files = {}

    def ids(self, key):
        if key not in self.lineage:
            self.lineage[key] = str(uuid.uuid5(NAMESPACE, self.model["nome"] + "/" + key))
        return self.lineage[key]

    def short_id(self, key):
        return self.ids(key).replace("-", "")[:20]

    def json(self, path, document):
        self.files[path] = json.dumps(document, indent=2, ensure_ascii=False) + "\n"

    def text(self, path, content):
        self.files[path] = content

    def field(self, name):
        kind = "Measure" if self.model["nomes"][name] == "medida" else "Column"
        return {kind: {"Expression": {"SourceRef": {"Entity": self.model["tabela"]}}, "Property": name}}

    def projection(self, name):
        field = self.field(name)
        query_ref = name if "Measure" in field else self.model["tabela"] + "." + name
        return {"field": field, "queryRef": query_ref, "nativeQueryRef": name}

    # -- modelo semântico ---------------------------------------------------

    def semantic_model(self, folder):
        model = self.model
        table = model["tabela"]
        self.json(folder + "/definition.pbism", {
            "$schema": ITEM + "semanticModel/definitionProperties/1.0.0/schema.json",
            "version": "4.0", "settings": {}})
        self.platform(folder, "SemanticModel")
        self.text(folder + "/definition/database.tmdl", "database\n\tcompatibilityLevel: 1601\n\n")
        self.text(folder + "/definition/model.tmdl", "\n".join([
            "model Model",
            "\tculture: pt-BR",
            "\tdefaultPowerBIDataSourceVersion: powerBI_V3",
            "\tsourceQueryCulture: pt-BR",
            "\tdataAccessOptions",
            "\t\tlegacyRedirects",
            "\t\treturnErrorValuesAsNull",
            "",
            f'annotation PBI_QueryOrder = ["{PARAMETER}","{table}"]',
            "",
            'annotation PBI_ProTooling = ["DevMode"]',
            "",
            f"ref table {table}",
            "", ""]))
        self.text(folder + "/definition/expressions.tmdl", "\n".join([
            f"expression {PARAMETER} = {m_string(model['csv'].as_posix())} meta [IsParameterQuery=true, "
            'Type="Text", IsParameterQueryRequired=true]',
            f"\tlineageTag: {self.ids('parametro/' + PARAMETER)}",
            "",
            "\tannotation PBI_ResultType = Text",
            "", ""]))
        lines = [f"table {table}", f"\tlineageTag: {self.ids('tabela/' + table)}", ""]
        for item in model["medidas"]:
            lines.append(f"\tmeasure {tmdl_name(item['nome'])} = {item['dax']}")
            if item.get("formato"):
                lines.append(f"\t\tformatString: {item['formato']}")
            lines += [f"\t\tlineageTag: {self.ids('medida/' + item['nome'])}", ""]
        for column, kind in model["colunas"].items():
            lines += [f"\tcolumn {tmdl_name(column)}", f"\t\tdataType: {TYPES[kind]}"]
            if kind == "inteiro":
                lines.append("\t\tformatString: 0")
            lines += [f"\t\tlineageTag: {self.ids('coluna/' + column)}", "\t\tsummarizeBy: none",
                      f"\t\tsourceColumn: {column}", ""]
        for item in model["colunas_calculadas"]:
            lines += [f"\tcolumn {tmdl_name(item['nome'])} = {item['dax']}",
                      f"\t\tdataType: {TYPES[item.get('tipo', 'texto')]}",
                      f"\t\tlineageTag: {self.ids('coluna/' + item['nome'])}", "\t\tsummarizeBy: none", ""]
        lines += [f"\tpartition {table} = m", "\t\tmode: import", "\t\tsource ="]
        lines += ["\t\t\t\t" + line for line in self.query().splitlines()]
        self.text(folder + f"/definition/tables/{table}.tmdl", "\n".join(lines) + "\n\n")

    def query(self):
        model = self.model
        selected = ", ".join(m_string(c) for c in model["colunas"])
        conversions = []
        for column, kind in model["colunas"].items():
            if kind == "texto":
                conversions.append("{" + m_string(column) + ", each if _ = null then null else Text.From(_), type text}")
            else:
                number = "Number.FromText(_, \"en-US\")"
                if kind == "inteiro":
                    number = f"Int64.From({number})"
                kind_m = "Int64.Type" if kind == "inteiro" else "type number"
                conversions.append("{" + m_string(column) + f', each if _ = null or _ = "" then null else {number}, {kind_m}' + "}")
        return "\n".join([
            "let",
            f"    Fonte = Csv.Document(File.Contents({PARAMETER}), [Delimiter={m_string(model['separador'])}, "
            "Encoding=65001, QuoteStyle=QuoteStyle.Csv]),",
            "    Cabecalhos = Table.PromoteHeaders(Fonte, [PromoteAllScalars=true]),",
            f"    Colunas = Table.SelectColumns(Cabecalhos, {{{selected}}}),",
            f"    Tipos = Table.TransformColumns(Colunas, {{{', '.join(conversions)}}})",
            "in",
            "    Tipos"])

    def platform(self, folder, kind):
        self.json(folder + "/.platform", {
            "$schema": FABRIC + "gitIntegration/platformProperties/2.0.0/schema.json",
            "metadata": {"type": kind, "displayName": self.model["titulo"]},
            "config": {"version": "2.0", "logicalId": self.ids("plataforma/" + kind)}})

    # -- relatório ----------------------------------------------------------

    def report(self, folder, model_folder):
        self.json(folder + "/definition.pbir", {
            "$schema": ITEM + "report/definitionProperties/2.0.0/schema.json",
            "version": "4.0", "datasetReference": {"byPath": {"path": "../" + model_folder}}})
        self.platform(folder, "Report")
        base = folder + "/definition"
        self.json(base + "/version.json", {
            "$schema": ITEM + "report/definition/versionMetadata/1.0.0/schema.json", "version": "2.0.0"})
        self.json(base + "/report.json", {
            "$schema": ITEM + "report/definition/report/3.3.0/schema.json",
            "themeCollection": {"baseTheme": {
                "name": "CY24SU10",
                "reportVersionAtImport": {"visual": "1.8.91", "report": "2.0.91", "page": "1.3.91"},
                "type": "SharedResources"}}})
        page_ids = [self.short_id("pagina/" + p["nome"]) for p in self.model["paginas"]]
        self.json(base + "/pages/pages.json", {
            "$schema": ITEM + "report/definition/pagesMetadata/1.0.0/schema.json",
            "pageOrder": page_ids, "activePageName": page_ids[0]})
        for page, page_id in zip(self.model["paginas"], page_ids):
            self.page(base + "/pages/" + page_id, page, page_id)

    def page(self, folder, page, page_id):
        self.json(folder + "/page.json", {
            "$schema": ITEM + "report/definition/page/2.0.0/schema.json",
            "name": page_id, "displayName": page["nome"], "displayOption": "FitToPage",
            "height": PAGE_HEIGHT, "width": PAGE_WIDTH,
            "objects": {"background": [{"properties": {
                "color": {"solid": {"color": text_literal("#F3F6FA")}}, "transparency": literal("0D")}}]}})
        decorations = []
        if page.get("titulo"):
            decorations.append(("titulo", page["titulo"], [24, 6, 1232, 54], "20pt", TEXT_COLOR))
        if page.get("subtitulo"):
            decorations.append(("subtitulo", page["subtitulo"], [24, 58, 1232, 36], "12pt", SOFT_COLOR))
        if page.get("nota"):
            decorations.append(("nota", page["nota"], [24, NOTE_TOP + 2, 1232, PAGE_HEIGHT - NOTE_TOP - 2], "9pt", SOFT_COLOR))
        key = "pagina/" + page["nome"]
        for name, text, position, size, color in decorations:
            spec = {"tipo": "texto", "texto": text, "tamanho_fonte": size, "posicao": position}
            self.visual(folder, key + "/" + name, spec, color)
        for index, spec in enumerate(page["visuais"], start=1):
            self.visual(folder, f"{key}/visual/{index}", spec)

    def visual(self, page_folder, key, spec, text_color=TEXT_COLOR):
        kind = spec["tipo"]
        visual_type = VISUAL_TYPES[kind]
        name = self.short_id(key)
        x, y, w, h = spec["posicao"]
        config = {"visualType": visual_type, "drillFilterOtherVisuals": True}
        objects = {}
        containers = {}
        if kind == "texto":
            paragraphs = spec["texto"] if isinstance(spec["texto"], list) else [spec["texto"]]
            containers["title"] = [{"properties": {"show": literal("false")}}]
            objects["general"] = [{"properties": {"paragraphs": [
                {"textRuns": [{"value": paragraph, "textStyle": {
                    "fontFamily": "Segoe UI", "fontSize": spec.get("tamanho_fonte", "11pt"), "color": text_color}}]}
                for paragraph in paragraphs]}}]
        else:
            containers["title"] = [{"properties": {
                "show": literal("true"), "text": text_literal(spec["titulo"]), "fontSize": literal("12D"),
                "titleWrap": literal("true"), "fontColor": {"solid": {"color": text_literal(TEXT_COLOR)}}}}]
            if spec.get("subtitulo"):
                containers["subTitle"] = [{"properties": {
                    "show": literal("true"), "text": text_literal(spec["subtitulo"]), "fontSize": literal("9D"),
                    "titleWrap": literal("true"), "fontColor": {"solid": {"color": text_literal(SOFT_COLOR)}}}}]
            containers["background"] = [{"properties": {
                "color": {"solid": {"color": text_literal("#FFFFFF")}}, "transparency": literal("0D")}}]
            roles = self.roles(kind, spec)
            config["query"] = {"queryState": {
                role: {"projections": [self.projection(field) for field in fields]}
                for role, fields in roles.items()}}
            sort = self.sort(kind, spec)
            if sort:
                config["query"]["sortDefinition"] = {"sort": [sort], "isDefaultSort": False}
            objects.update(self.objects(kind))
            if spec.get("escala_log"):
                objects["categoryAxis"][0]["properties"]["logAxisScale"] = literal("true")
        config["visualContainerObjects"] = containers
        if objects:
            config["objects"] = objects
        document = {
            "$schema": ITEM + "report/definition/visualContainer/2.1.0/schema.json",
            "name": name,
            "position": {"x": x, "y": y, "z": 0, "height": h, "width": w, "tabOrder": 0},
            "visual": config}
        if spec.get("top"):
            document["filterConfig"] = {"filters": [self.top_filter(name, spec)]}
        self.json(page_folder + f"/visuals/{name}/visual.json", document)

    @staticmethod
    def roles(kind, spec):
        def listify(value):
            return value if isinstance(value, list) else [value]

        if kind == "cartao":
            return {"Values": [spec["medida"]]}
        if kind in ("barras", "colunas", "linhas"):
            roles = {"Category": [spec["categoria"]], "Y": listify(spec["valor"])}
            if spec.get("serie"):
                roles["Series"] = [spec["serie"]]
            return roles
        if kind == "dispersao":
            roles = {"Category": [spec["detalhe"]], "X": [spec["x"]], "Y": [spec["y"]]}
            if spec.get("legenda"):
                roles["Series"] = [spec["legenda"]]
            if spec.get("tamanho"):
                roles["Size"] = [spec["tamanho"]]
            return roles
        if kind == "tabela":
            return {"Values": list(spec["campos"])}
        return {"Values": [spec["campo"]]}

    def sort(self, kind, spec):
        if kind in ("barras", "colunas"):
            if spec.get("ordenar", "valor") == "valor":
                return {"field": self.field(spec["valor"]), "direction": "Descending"}
            return {"field": self.field(spec["categoria"]), "direction": "Ascending"}
        if kind == "linhas":
            return {"field": self.field(spec["categoria"]), "direction": "Ascending"}
        return None

    @staticmethod
    def objects(kind):
        if kind == "cartao":
            return {"labels": [{"properties": {"fontSize": literal("28D"), "labelDisplayUnits": literal("1D")}}],
                    "categoryLabels": [{"properties": {"show": literal("false")}}]}
        if kind in ("barras", "colunas"):
            objects = {"labels": [{"properties": {"show": literal("true")}}]}
            if kind == "barras":
                objects["categoryAxis"] = [{"properties": {
                    "fontSize": literal("10D"), "showAxisTitle": literal("false")}}]
            return objects
        if kind == "linhas":
            return {"categoryAxis": [{"properties": {"axisType": text_literal("Categorical")}}],
                    "lineStyles": [{"properties": {"showMarker": literal("true")}}],
                    "labels": [{"properties": {"show": literal("true")}}]}
        if kind == "dispersao":
            return {"categoryAxis": [{"properties": {"showAxisTitle": literal("true")}}],
                    "valueAxis": [{"properties": {"showAxisTitle": literal("true")}}]}
        if kind == "tabela":
            return {"grid": [{"properties": {"rowPadding": literal("4D")}}],
                    "columnHeaders": [{"properties": {"wordWrap": literal("true")}}],
                    "values": [{"properties": {"wordWrap": literal("true")}}]}
        if kind == "segmentacao":
            return {"data": [{"properties": {"mode": text_literal("Dropdown")}}],
                    "header": [{"properties": {"show": literal("false")}}]}
        return {}

    def top_filter(self, name, spec):
        """Filtro "N primeiros" na categoria, ordenado pela medida do visual."""
        table = self.model["tabela"]
        category, value = spec["categoria"], spec["valor"]
        source = {"SourceRef": {"Source": "t"}}
        return {
            "name": "top_" + name,
            "field": self.field(category),
            "type": "TopN",
            "filter": {
                "Version": 2,
                "From": [
                    {"Name": "subquery", "Expression": {"Subquery": {"Query": {
                        "Version": 2,
                        "From": [{"Name": "t", "Entity": table, "Type": 0}],
                        "Select": [{"Column": {"Expression": source, "Property": category}, "Name": "field"}],
                        "OrderBy": [{"Direction": 2, "Expression": {
                            "Measure": {"Expression": source, "Property": value}}}],
                        "Top": spec["top"]}}}, "Type": 2},
                    {"Name": "t", "Entity": table, "Type": 0}],
                "Where": [{"Condition": {"In": {
                    "Expressions": [{"Column": {"Expression": source, "Property": category}}],
                    "Table": {"SourceRef": {"Source": "subquery"}}}}}]}}

    def build(self):
        name = self.model["nome"]
        model_folder, report_folder = name + ".SemanticModel", name + ".Report"
        self.json(name + ".pbip", {
            "$schema": FABRIC + "pbip/pbipProperties/1.0.0/schema.json",
            "version": "1.0", "artifacts": [{"report": {"path": report_folder}}],
            "settings": {"enableAutoRecovery": True}})
        self.text(".gitignore", "**/.pbi/localSettings.json\n**/.pbi/cache.abf\n")
        # O Desktop salva com CRLF; assim o Git não acusa mudança só por fim de linha.
        self.text(".gitattributes", "* text=auto eol=lf\n")
        self.semantic_model(model_folder)
        self.report(report_folder, model_folder)
        self.json(".lineage.json", dict(sorted(self.lineage.items())))
        self.json(".generated-files.json", sorted(list(self.files) + [".generated-files.json"]))
        return self.files


# ---------------------------------------------------------------------------
# Conferência dos arquivos gerados
# ---------------------------------------------------------------------------

def check_files(folder, model):
    """Confere codificação, JSON e se cada campo usado nos visuais existe no modelo."""
    count = 0
    for path in sorted(folder.rglob("*")):
        if not path.is_file():
            continue
        data = path.read_bytes()
        if data.startswith(b"\xef\xbb\xbf") or b"\r\n" in data:
            raise ValueError(f"Arquivo com BOM ou fim de linha do Windows: {path}")
        if path.suffix in (".json", ".pbip", ".pbir", ".pbism") or path.name == ".platform":
            document = json.loads(data.decode("utf-8"))
            count += 1
            if path.name == "visual.json":
                state = document["visual"].get("query", {}).get("queryState", {})
                for role in state.values():
                    for projection in role["projections"]:
                        (kind, expr), = projection["field"].items()
                        expected = "medida" if kind == "Measure" else "coluna"
                        if model["nomes"].get(expr["Property"]) != expected:
                            raise ValueError(f"{path}: campo inexistente {expr['Property']}")
    return count


def cached_schema(url):
    url = url.replace("/schema.embedded.json", "/schema-embedded.json")
    if not url.startswith("https://developer.microsoft.com/json-schemas/"):
        raise ValueError("Esquema fora do endereço oficial da Microsoft: " + url)
    import urllib.request

    folder = Path.home() / ".cache" / "painel-powerbi-esquemas"
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / (hashlib.sha256(url.encode()).hexdigest()[:20] + ".json")
    if target.exists():
        return json.loads(target.read_text(encoding="utf-8"))
    with urllib.request.urlopen(url, timeout=30) as response:
        schema = json.load(response)
    target.write_text(json.dumps(schema, ensure_ascii=False), encoding="utf-8")
    return schema


def check_schemas(folder):
    try:
        import jsonschema
    except ImportError:
        raise SystemExit("A opção --validar-esquemas precisa do pacote jsonschema: "
                         "python -m pip install jsonschema") from None
    import warnings

    warnings.filterwarnings("ignore", category=DeprecationWarning)
    from jsonschema import RefResolver

    count = 0
    for path in sorted(folder.rglob("*")):
        if not path.is_file() or (path.suffix not in (".json", ".pbip", ".pbir", ".pbism")
                                  and path.name != ".platform"):
            continue
        document = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(document, dict) and "$schema" in document:
            schema = cached_schema(document["$schema"])
            resolver = RefResolver(base_uri=document["$schema"], referrer=schema,
                                   handlers={"https": cached_schema})
            jsonschema.validators.validator_for(schema)(schema, resolver=resolver).validate(document)
            count += 1
    return count


# ---------------------------------------------------------------------------
# Gravação segura
# ---------------------------------------------------------------------------

def generate(spec_path, output=None, force=False, dry_run=False, schemas=False):
    spec_path = Path(spec_path).resolve()
    model = load_spec(spec_path)
    destination = Path(output).resolve() if output else spec_path.parent / "pbip"
    manifest_path = destination / ".generated-files.json"
    if not dry_run and not force:
        if manifest_path.exists():
            raise FileExistsError(f"Já existe um painel gerado em {destination}. Use --force para gerar "
                                  "de novo; os arquivos que você criou nessa pasta são preservados.")
        if destination.exists() and any(destination.iterdir()):
            raise FileExistsError(f"A pasta {destination} já tem arquivos. Escolha outra com --saida "
                                  "ou use --force.")
    lineage_path = destination / ".lineage.json"
    lineage = json.loads(lineage_path.read_text(encoding="utf-8")) if lineage_path.exists() else {}
    files = Builder(model, lineage).build()

    # Gera e confere numa pasta temporária antes de tocar na pasta que o Desktop abre.
    with tempfile.TemporaryDirectory(prefix="painel-powerbi-") as tmp:
        stage = Path(tmp)
        for relative, content in files.items():
            target = stage / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content.encode("utf-8"))
        checked = check_files(stage, model)
        validated = check_schemas(stage) if schemas else 0
        if not dry_run:
            old = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else []
            for relative in old:
                target = (destination / relative).resolve()
                if destination not in target.parents:
                    raise ValueError("O manifesto aponta para fora da pasta do painel: " + relative)
                if relative not in files and target.is_file():
                    target.unlink()
            for relative in files:
                target = destination / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(stage / relative, target)

    visuals = sum(len(p["visuais"]) for p in model["paginas"])
    notes = [f"O caminho do CSV foi gravado como {model['csv'].as_posix()}. Se mover a pasta do "
             "projeto, gere o painel de novo."]
    if platform.system() != "Windows":
        notes.append("O Power BI Desktop só roda no Windows. Leve a pasta inteira para um computador "
                     "com Windows e gere de novo lá, para atualizar o caminho do CSV.")
    return {
        "situacao": "conferido, nada gravado (--dry-run)" if dry_run else "gerado",
        "projeto": str(destination / (model["nome"] + ".pbip")),
        "linhas_no_csv": model["linhas_csv"],
        "paginas": len(model["paginas"]),
        "visuais": visuals,
        "medidas": [m["nome"] for m in model["medidas"]],
        "arquivos_json_conferidos": checked,
        "arquivos_validados_com_esquema_oficial": validated if schemas else "não pedido",
        "avisos": notes,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Gera um projeto .pbip a partir de uma especificação JSON.")
    parser.add_argument("especificacao", help="arquivo JSON com a especificação do painel")
    parser.add_argument("--saida", help="pasta do projeto gerado (padrão: pbip/, ao lado da especificação)")
    parser.add_argument("--force", action="store_true",
                        help="gera de novo sobre um painel já gerado, preservando arquivos seus")
    parser.add_argument("--dry-run", action="store_true", help="só confere, sem gravar nada")
    parser.add_argument("--validar-esquemas", action="store_true",
                        help="confere com os esquemas oficiais (precisa de jsonschema e internet)")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        result = generate(args.especificacao, args.saida, args.force, args.dry_run, args.validar_esquemas)
    except SpecError as error:
        print("A especificação tem problemas:\n" + str(error), file=sys.stderr)
        return 2
    except FileExistsError as error:
        print(str(error), file=sys.stderr)
        return 3
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
