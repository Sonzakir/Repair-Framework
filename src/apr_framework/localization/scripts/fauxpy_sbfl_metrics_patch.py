from importlib.util import find_spec
from pathlib import Path

spec = find_spec("fauxpy")
if spec is None or spec.origin is None:
    raise SystemExit("Cannot patch FauxPy because the fauxpy package is not importable.")

package_root = Path(spec.origin).parent
sbfl_root = package_root / "fault_localization" / "sbfl"


def read(path):
    return path.read_text(encoding="utf-8")


def write(path, text):
    path.write_text(text, encoding="utf-8")


def replace_once(text, old, new, label, marker=None):
    if (marker is not None and marker in text) or new in text:
        return text
    if old not in text:
        raise SystemExit(f"Cannot apply FauxPy SBFL metric patch: expected {label} was not found.")
    return text.replace(old, new, 1)


metric_path = sbfl_root / "metric_jaccard.py"
write(
    metric_path,
    '''class MetricJaccard:
    def __init__(self, epsilon: float):
        self._metric_name = "Jaccard"
        self._epsilon = epsilon

    def get_metric_name(self):
        return self._metric_name

    def compute(self, ef, ep, nf, np):
        score = float(ef) / (ef + ep + nf + self._epsilon)
        return score
''',
)

metric_path = sbfl_root / "metric_sbi.py"
write(
    metric_path,
    '''class MetricSBI:
    def __init__(self, epsilon: float):
        self._metric_name = "SBI"
        self._epsilon = epsilon

    def get_metric_name(self):
        return self._metric_name

    def compute(self, ef, ep, nf, np):
        total = ef + ep
        if total == 0:
            return 0.0
        score = float(ef) / total
        return score
''',
)

ranking_path = sbfl_root / "ranking_metric_manager.py"
ranking_text = read(ranking_path)
ranking_text = replace_once(
    ranking_text,
    "from fauxpy.fault_localization.sbfl.metric_dstar import MetricDstar\n",
    "from fauxpy.fault_localization.sbfl.metric_dstar import MetricDstar\n"
    "from fauxpy.fault_localization.sbfl.metric_jaccard import MetricJaccard\n",
    "ranking metric imports",
    "from fauxpy.fault_localization.sbfl.metric_jaccard import MetricJaccard\n",
)
ranking_text = replace_once(
    ranking_text,
    "from fauxpy.fault_localization.sbfl.metric_jaccard import MetricJaccard\n",
    "from fauxpy.fault_localization.sbfl.metric_jaccard import MetricJaccard\n"
    "from fauxpy.fault_localization.sbfl.metric_sbi import MetricSBI\n",
    "ranking SBI metric import",
)
ranking_text = replace_once(
    ranking_text,
    "            MetricDstar(self.EPSILON),\n        ]",
    "            MetricDstar(self.EPSILON),\n"
    "            MetricJaccard(self.EPSILON),\n"
    "        ]",
    "ranking metric list",
    "            MetricJaccard(self.EPSILON),\n",
)
ranking_text = replace_once(
    ranking_text,
    "            MetricJaccard(self.EPSILON),\n",
    "            MetricJaccard(self.EPSILON),\n"
    "            MetricSBI(self.EPSILON),\n",
    "ranking SBI metric list",
)
write(ranking_path, ranking_text)

db_path = sbfl_root / "db_manager.py"
db_text = read(db_path)
db_text = replace_once(
    db_text,
    '            f"Dstar REAL NOT NULL);"\n',
    '            f"Dstar REAL NOT NULL, "\n'
    '            f"Jaccard REAL NOT NULL);"\n',
    "score table schema",
    '            f"Jaccard REAL NOT NULL',
)
db_text = replace_once(
    db_text,
    '            f"Jaccard REAL NOT NULL);"\n',
    '            f"Jaccard REAL NOT NULL, "\n'
    '            f"SBI REAL NOT NULL);"\n',
    "SBI score table schema",
)
db_text = replace_once(
    db_text,
    '        score_dstar_table_index_command = (\n'
    '            f"CREATE INDEX index_Dstar ON {self._Score_table} (Dstar);"\n'
    '        )\n',
    '        score_dstar_table_index_command = (\n'
    '            f"CREATE INDEX index_Dstar ON {self._Score_table} (Dstar);"\n'
    '        )\n'
    '\n'
    '        score_jaccard_table_index_command = (\n'
    '            f"CREATE INDEX index_Jaccard ON {self._Score_table} (Jaccard);"\n'
    '        )\n',
    "score indexes",
    "score_jaccard_table_index_command",
)
db_text = replace_once(
    db_text,
    '        score_jaccard_table_index_command = (\n'
    '            f"CREATE INDEX index_Jaccard ON {self._Score_table} (Jaccard);"\n'
    '        )\n',
    '        score_jaccard_table_index_command = (\n'
    '            f"CREATE INDEX index_Jaccard ON {self._Score_table} (Jaccard);"\n'
    '        )\n'
    '\n'
    '        score_sbi_table_index_command = (\n'
    '            f"CREATE INDEX index_SBI ON {self._Score_table} (SBI);"\n'
    '        )\n',
    "SBI score index",
)
db_text = replace_once(
    db_text,
    "            score_dstar_table_index_command,\n"
    "            view_create_command,\n",
    "            score_dstar_table_index_command,\n"
    "            score_jaccard_table_index_command,\n"
    "            view_create_command,\n",
    "schema command list",
    "            score_jaccard_table_index_command,\n",
)
db_text = replace_once(
    db_text,
    "            score_jaccard_table_index_command,\n"
    "            view_create_command,\n",
    "            score_jaccard_table_index_command,\n"
    "            score_sbi_table_index_command,\n"
    "            view_create_command,\n",
    "SBI schema command list",
)
db_text = replace_once(
    db_text,
    '            f"VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?)",\n',
    '            f"VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?)",\n',
    "score insert placeholders",
    '            f"VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?',
)
db_text = replace_once(
    db_text,
    '            f"VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?)",\n',
    '            f"VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",\n',
    "SBI score insert placeholders",
)
db_text = replace_once(
    db_text,
    '                scores["Dstar"],\n'
    "            ),\n",
    '                scores["Dstar"],\n'
    '                scores["Jaccard"],\n'
    "            ),\n",
    "score insert values",
    '                scores["Jaccard"],\n',
)
db_text = replace_once(
    db_text,
    '                scores["Jaccard"],\n'
    "            ),\n",
    '                scores["Jaccard"],\n'
    '                scores["SBI"],\n'
    "            ),\n",
    "SBI score insert values",
)
db_text = replace_once(
    db_text,
    '        cur.execute(\n'
    '            f"SELECT Entity, Dstar FROM {self._Score_table} ORDER BY Dstar DESC LIMIT ?",\n'
    '            (top_n,),\n'
    '        )\n'
    '        score_dstar = cur.fetchall()\n'
    '\n'
    '        ranked_entities = {\n'
    '            "Tarantula": score_tarantula,\n'
    '            "Ochiai": score_ochiai,\n'
    '            "Dstar": score_dstar,\n'
    '        }\n',
    '        cur.execute(\n'
    '            f"SELECT Entity, Dstar FROM {self._Score_table} ORDER BY Dstar DESC LIMIT ?",\n'
    '            (top_n,),\n'
    '        )\n'
    '        score_dstar = cur.fetchall()\n'
    '\n'
    '        cur.execute(\n'
    '            f"SELECT Entity, Jaccard FROM {self._Score_table} ORDER BY Jaccard DESC LIMIT ?",\n'
    '            (top_n,),\n'
    '        )\n'
    '        score_jaccard = cur.fetchall()\n'
    '\n'
    '        ranked_entities = {\n'
    '            "Tarantula": score_tarantula,\n'
    '            "Ochiai": score_ochiai,\n'
    '            "Dstar": score_dstar,\n'
    '            "Jaccard": score_jaccard,\n'
    '        }\n',
    "top-n Jaccard query",
    '            f"SELECT Entity, Jaccard FROM {self._Score_table} ORDER BY Jaccard DESC LIMIT ?",\n',
)
db_text = replace_once(
    db_text,
    '        cur.execute(\n'
    '            f"SELECT Entity, Jaccard FROM {self._Score_table} ORDER BY Jaccard DESC LIMIT ?",\n'
    '            (top_n,),\n'
    '        )\n'
    '        score_jaccard = cur.fetchall()\n'
    '\n'
    '        ranked_entities = {\n'
    '            "Tarantula": score_tarantula,\n'
    '            "Ochiai": score_ochiai,\n'
    '            "Dstar": score_dstar,\n'
    '            "Jaccard": score_jaccard,\n'
    '        }\n',
    '        cur.execute(\n'
    '            f"SELECT Entity, Jaccard FROM {self._Score_table} ORDER BY Jaccard DESC LIMIT ?",\n'
    '            (top_n,),\n'
    '        )\n'
    '        score_jaccard = cur.fetchall()\n'
    '\n'
    '        cur.execute(\n'
    '            f"SELECT Entity, SBI FROM {self._Score_table} ORDER BY SBI DESC LIMIT ?",\n'
    '            (top_n,),\n'
    '        )\n'
    '        score_sbi = cur.fetchall()\n'
    '\n'
    '        ranked_entities = {\n'
    '            "Tarantula": score_tarantula,\n'
    '            "Ochiai": score_ochiai,\n'
    '            "Dstar": score_dstar,\n'
    '            "Jaccard": score_jaccard,\n'
    '            "SBI": score_sbi,\n'
    '        }\n',
    "top-n SBI query",
)
db_text = replace_once(
    db_text,
    '        cur.execute(\n'
    '            f"SELECT Entity, Dstar FROM {self._Score_table} ORDER BY Dstar DESC"\n'
    '        )\n'
    '        score_dstar = cur.fetchall()\n'
    '\n'
    '        ranked_entities = {\n'
    '            "Tarantula": score_tarantula,\n'
    '            "Ochiai": score_ochiai,\n'
    '            "Dstar": score_dstar,\n'
    '        }\n',
    '        cur.execute(\n'
    '            f"SELECT Entity, Dstar FROM {self._Score_table} ORDER BY Dstar DESC"\n'
    '        )\n'
    '        score_dstar = cur.fetchall()\n'
    '\n'
    '        cur.execute(\n'
    '            f"SELECT Entity, Jaccard FROM {self._Score_table} ORDER BY Jaccard DESC"\n'
    '        )\n'
    '        score_jaccard = cur.fetchall()\n'
    '\n'
    '        ranked_entities = {\n'
    '            "Tarantula": score_tarantula,\n'
    '            "Ochiai": score_ochiai,\n'
    '            "Dstar": score_dstar,\n'
    '            "Jaccard": score_jaccard,\n'
    '        }\n',
    "all-ranks Jaccard query",
    '            f"SELECT Entity, Jaccard FROM {self._Score_table} ORDER BY Jaccard DESC"\n',
)
db_text = replace_once(
    db_text,
    '        cur.execute(\n'
    '            f"SELECT Entity, Jaccard FROM {self._Score_table} ORDER BY Jaccard DESC"\n'
    '        )\n'
    '        score_jaccard = cur.fetchall()\n'
    '\n'
    '        ranked_entities = {\n'
    '            "Tarantula": score_tarantula,\n'
    '            "Ochiai": score_ochiai,\n'
    '            "Dstar": score_dstar,\n'
    '            "Jaccard": score_jaccard,\n'
    '        }\n',
    '        cur.execute(\n'
    '            f"SELECT Entity, Jaccard FROM {self._Score_table} ORDER BY Jaccard DESC"\n'
    '        )\n'
    '        score_jaccard = cur.fetchall()\n'
    '\n'
    '        cur.execute(\n'
    '            f"SELECT Entity, SBI FROM {self._Score_table} ORDER BY SBI DESC"\n'
    '        )\n'
    '        score_sbi = cur.fetchall()\n'
    '\n'
    '        ranked_entities = {\n'
    '            "Tarantula": score_tarantula,\n'
    '            "Ochiai": score_ochiai,\n'
    '            "Dstar": score_dstar,\n'
    '            "Jaccard": score_jaccard,\n'
    '            "SBI": score_sbi,\n'
    '        }\n',
    "all-ranks SBI query",
)
write(db_path, db_text)
print("FauxPy SBFL metric patch applied.")
