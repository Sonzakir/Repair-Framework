import re
import shlex
import sqlite3
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, overload

from apr_framework.core.exceptions import ConfigurationError
from apr_framework.core.models import (
    BugIdentifier,
    CheckoutResult,
    LocalizationResult,
    RankedLocation,
    TestRunResult,
)
from apr_framework.localization.base import FaultLocalizer

FAUXPY_INSTALL_REQUIREMENT = "fauxpy==0.7.0"

_FAUXPY_SBFL_METRICS_PATCH_SCRIPT = r"""
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
        self._metric_name = \"Jaccard\"
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
        self._metric_name = \"SBI\"
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
"""

_FAUXPY_MBFL_SELECTION_PATCH_SCRIPT = r"""
from importlib.util import find_spec
from pathlib import Path

spec = find_spec("fauxpy")
if spec is None or spec.origin is None:
    raise SystemExit("Cannot patch FauxPy because the fauxpy package is not importable.")

package_root = Path(spec.origin).parent


def read(path):
    return path.read_text(encoding="utf-8")


def write(path, text):
    path.write_text(text, encoding="utf-8")


def replace_once(text, old, new, label):
    if new in text:
        return text
    if old not in text:
        raise SystemExit(f"Cannot apply FauxPy MBFL selection patch: expected {label} was not found.")
    return text.replace(old, new, 1)


pytest_manager_path = package_root / "command_line" / "pytest_mode" / "pytest_option_manager.py"
pytest_text = read(pytest_manager_path)
pytest_text = replace_once(
    pytest_text,
    '''        group.addoption(
            "--fauxpy-verbose",
            action="store_true",
            default=False,
            help="Show detailed output from FauxPy plugin.",
        )
''',
    '''        group.addoption(
            "--fauxpy-verbose",
            action="store_true",
            default=False,
            help="Show detailed output from FauxPy plugin.",
        )
        group.addoption(
            "--mutation-selection",
            default=None,
            help="Select a framework-level MBFL mutation selection strategy.",
        )
        group.addoption(
            "--mutation-budget",
            default=None,
            help="Maximum number of mutants to validate for selected MBFL strategies.",
        )
        group.addoption(
            "--mutation-seed",
            default="0",
            help="Random seed used by framework-level MBFL mutation selection.",
        )
''',
    "pytest MBFL selection options",
)
pytest_text = replace_once(
    pytest_text,
    '''        fauxpy_verbose_opt = pytest_config.getoption("--fauxpy-verbose")
        file_or_dir = pytest_config.getoption("file_or_dir")
''',
    '''        fauxpy_verbose_opt = pytest_config.getoption("--fauxpy-verbose")
        mutation_selection_opt = pytest_config.getoption("--mutation-selection")
        mutation_budget_opt = pytest_config.getoption("--mutation-budget")
        mutation_seed_opt = pytest_config.getoption("--mutation-seed")
        file_or_dir = pytest_config.getoption("file_or_dir")
''',
    "pytest MBFL selection option reads",
)
pytest_text = replace_once(
    pytest_text,
    '''            fauxpy_verbose_opt,
            file_or_dir,
        )
''',
    '''            fauxpy_verbose_opt,
            file_or_dir,
            mutation_selection_opt,
            mutation_budget_opt,
            mutation_seed_opt,
        )
''',
    "pytest MBFL selection constructor args",
)
write(pytest_manager_path, pytest_text)

fl_option_manager_path = package_root / "command_line" / "pytest_mode" / "fl_option_manager.py"
fl_text = read(fl_option_manager_path)
fl_text = replace_once(
    fl_text,
    '''        fauxpy_verbose_opt: bool,
        file_or_dir,
    ):
''',
    '''        fauxpy_verbose_opt: bool,
        file_or_dir,
        mutation_selection_opt: str,
        mutation_budget_opt: str,
        mutation_seed_opt: str,
    ):
''',
    "FlOptionManager MBFL selection signature",
)
fl_text = replace_once(
    fl_text,
    '''        self._file_or_dir_opt = file_or_dir
        self._path_manager = FlPathManager(
''',
    '''        self._file_or_dir_opt = file_or_dir
        self._mutation_selection = mutation_selection_opt
        self._mutation_budget = mutation_budget_opt
        self._mutation_seed = mutation_seed_opt
        self._path_manager = FlPathManager(
''',
    "FlOptionManager MBFL selection fields",
)
fl_text = replace_once(
    fl_text,
    '''                self._file_or_dir_opt,
                report_directory_path,
                Path(self._project_working_directory.get_absolute()),
            )
''',
    '''                self._file_or_dir_opt,
                report_directory_path,
                Path(self._project_working_directory.get_absolute()),
                self._mutation_selection,
                self._mutation_budget,
                self._mutation_seed,
            )
''',
    "MbflSession MBFL selection args",
)
write(fl_option_manager_path, fl_text)

mbfl_session_path = package_root / "fault_localization" / "mbfl" / "session_lib.py"
mbfl_session_text = read(mbfl_session_path)
mbfl_session_text = replace_once(
    mbfl_session_text,
    '''        file_or_dir,
        report_directory_path: Path,
        project_working_directory: Path,
    ):
''',
    '''        file_or_dir,
        report_directory_path: Path,
        project_working_directory: Path,
        mutation_selection: str = None,
        mutation_budget: str = None,
        mutation_seed: str = "0",
    ):
''',
    "MbflSession MBFL selection signature",
)
mbfl_session_text = replace_once(
    mbfl_session_text,
    '''        self._mutation_manager = MutationManager(self._db_manager, self._mutation_strategy)
''',
    '''        self._mutation_manager = MutationManager(
            self._db_manager,
            self._mutation_strategy,
            mutation_selection,
            mutation_budget,
            mutation_seed,
        )
''',
    "MutationManager MBFL selection args",
)
write(mbfl_session_path, mbfl_session_text)

mutation_manager_path = package_root / "fault_localization" / "mbfl" / "mutation_manager.py"
mutation_text = read(mutation_manager_path)
mutation_text = replace_once(
    mutation_text,
    '''import logging
from pathlib import Path
''',
    '''import logging
import random
import time
from pathlib import Path
''',
    "MutationManager imports",
)
mutation_text = replace_once(
    mutation_text,
    '''    def __init__(
            self,
            db_manager: MbflDbManager,
            mutation_strategy: MutationStrategy
    ):
''',
    '''    def __init__(
            self,
            db_manager: MbflDbManager,
            mutation_strategy: MutationStrategy,
            mutation_selection: str = None,
            mutation_budget: str = None,
            mutation_seed: str = "0",
    ):
''',
    "MutationManager signature",
)
mutation_text = replace_once(
    mutation_text,
    '''        self._db_manager = db_manager
        self._mutation_strategy = mutation_strategy
''',
    '''        self._db_manager = db_manager
        self._mutation_strategy = mutation_strategy
        self._mutation_selection = mutation_selection
        self._mutation_budget = int(mutation_budget) if mutation_budget not in [None, ""] else None
        self._mutation_seed = int(mutation_seed or 0)
''',
    "MutationManager fields",
)
cosmic_ray_path = package_root / "fault_localization" / "mbfl" / "mutation_lib" / "cosmic_ray.py"
cosmic_ray_text = read(cosmic_ray_path)
cosmic_ray_text = replace_once(
    cosmic_ray_text,
    '''    def _get_all_mutant_list(
        self, module_path: str, operator_names: List[str]
    ) -> List[Mutant]:
''',
    '''    def _get_all_mutant_list(
        self,
        module_path: str,
        operator_names: List[str],
        line_numbers: Optional[List[int]] = None,
    ) -> List[Mutant]:
''',
    "Cosmic Ray line-limited mutant list signature",
)
cosmic_ray_text = replace_once(
    cosmic_ray_text,
    '''            for occurrence, (start_pos, end_pos) in enumerate(positions):
                original_code, mutated_code = self.produce_mutation(
                    module_path, operator, occurrence
                )
''',
    '''            for occurrence, (start_pos, end_pos) in enumerate(positions):
                if (
                    line_numbers is not None
                    and start_pos[0] not in line_numbers
                    and end_pos[0] not in line_numbers
                ):
                    continue

                original_code, mutated_code = self.produce_mutation(
                    module_path, operator, occurrence
                )
''',
    "Cosmic Ray line-limited mutation production",
)
cosmic_ray_text = replace_once(
    cosmic_ray_text,
    '''        mutant_list = self._get_all_mutant_list(module_path, operator_names)
''',
    '''        mutant_list = self._get_all_mutant_list(module_path, operator_names, line_numbers)
''',
    "Cosmic Ray line-limited call",
)
write(cosmic_ray_path, cosmic_ray_text)
old_get_all = '''    def get_all_mutants_for_failing_line_number_list(
        self, failing_line_number_list
    ) -> List:
        \"\"\"
         Generates mutants for the given statements. Each statement contains
          information about the module and the line number the statement belongs to.

         Args:
             failing_line_number_list (List[str]): A list of statements to generate mutants for.

         Returns:
             List[Mutant]: A list of mutants corresponding to the given statements.
         \"\"\"
        mutant_list = []

        for statement_name in failing_line_number_list:
            path, line_number = naming_lib.convert_statement_name_to_components(
                statement_name
            )
            self._db_manager.insert_failing_line_number_components(path, line_number)

        failing_module_path_list = (
            self._db_manager.select_distinct_failing_module_paths()
        )
        for module_path in failing_module_path_list:
            line_number_list = self._db_manager.select_failing_line_numbers_for_module_path(
                module_path
            )

            current_module_mutant_list = self._get_module_mutant_list(module_path, line_number_list)

            mutant_list += current_module_mutant_list

        self._set_mutant_ids(mutant_list)

        return mutant_list
'''
new_get_all = '''    def get_all_mutants_for_failing_line_number_list(
        self, failing_line_number_list
    ) -> List:
        \"\"\"
         Generates mutants for the given statements. Each statement contains
          information about the module and the line number the statement belongs to.

         Args:
             failing_line_number_list (List[str]): A list of statements to generate mutants for.

         Returns:
             List[Mutant]: A list of mutants corresponding to the given statements.
         \"\"\"
        candidate_statement_name_list = list(failing_line_number_list)
        selected_statement_name_list = list(candidate_statement_name_list)

        if self._mutation_selection == "random":
            rng = random.Random(self._mutation_seed)
            if (
                    self._mutation_budget is not None
                    and len(selected_statement_name_list) > self._mutation_budget
            ):
                selected_statement_name_list = rng.sample(
                    selected_statement_name_list,
                    self._mutation_budget,
                )
            else:
                rng.shuffle(selected_statement_name_list)

            fl_print.normal(f"Candidate mutation locations: {len(candidate_statement_name_list)}")
            fl_print.normal(f"Selected mutation locations: {len(selected_statement_name_list)}")

        generation_start = time.perf_counter()
        mutant_list = []

        for statement_name in selected_statement_name_list:
            path, line_number = naming_lib.convert_statement_name_to_components(
                statement_name
            )
            self._db_manager.insert_failing_line_number_components(path, line_number)

        failing_module_path_list = (
            self._db_manager.select_distinct_failing_module_paths()
        )
        for module_path in failing_module_path_list:
            line_number_list = self._db_manager.select_failing_line_numbers_for_module_path(
                module_path
            )

            current_module_mutant_list = self._get_module_mutant_list(module_path, line_number_list)

            mutant_list += current_module_mutant_list

        generated_mutant_count = len(mutant_list)
        if (
                self._mutation_selection == "random"
                and self._mutation_budget is not None
                and generated_mutant_count > self._mutation_budget
        ):
            rng = random.Random(self._mutation_seed)
            mutant_list = rng.sample(mutant_list, self._mutation_budget)

        self._set_mutant_ids(mutant_list)
        generation_time = time.perf_counter() - generation_start

        fl_print.normal(f"Total generated mutants: {generated_mutant_count}")
        fl_print.normal(f"Mutants selected for validation: {len(mutant_list)}")
        fl_print.normal(f"Mutation generation time: {generation_time:.4f}")

        return mutant_list
'''
mutation_text = replace_once(
    mutation_text,
    old_get_all,
    new_get_all,
    "MutationManager selection implementation",
)
write(mutation_manager_path, mutation_text)

mbfl_run_manager_path = package_root / "fault_localization" / "mbfl" / "mbfl_run_manager.py"
run_text = read(mbfl_run_manager_path)
run_text = replace_once(
    run_text,
    '''import shutil
from enum import Enum
''',
    '''import shutil
import time
from enum import Enum
''',
    "MbflRunManager imports",
)
run_text = replace_once(
    run_text,
    '''        number_of_all_mutants = len(mutants)

        fl_print.normal(f"Running {number_of_all_mutants} Mutants")
''',
    '''        number_of_all_mutants = len(mutants)
        validation_start = time.perf_counter()

        fl_print.normal(f"Running {number_of_all_mutants} Mutants")
''',
    "MbflRunManager validation timer start",
)
run_text = replace_once(
    run_text,
    '''        self._remove_temp_project(temp_project_path)
''',
    '''        validation_time = time.perf_counter() - validation_start
        fl_print.normal(f"Mutant validation time: {validation_time:.4f}")
        self._remove_temp_project(temp_project_path)
''',
    "MbflRunManager validation timer end",
)
write(mbfl_run_manager_path, run_text)

print("FauxPy MBFL selection patch applied.")
"""


def _completed_output(completed: subprocess.CompletedProcess[str]) -> str:
    return "\n".join(
        part
        for part in [
            (completed.stdout or "").strip(),
            (completed.stderr or "").strip(),
        ]
        if part
    )


def _validate_string_list(name: str, values: list[str]) -> None:
    if not isinstance(values, list):
        raise ConfigurationError(f"FauxPy {name} must be a list of strings")
    if any(not isinstance(value, str) for value in values):
        raise ConfigurationError(f"FauxPy {name} must contain only strings.")


def _parse_int_from_output(pattern: str, raw_output: str) -> int | None:
    match = re.search(pattern, raw_output)
    if match is None:
        return None
    return int(match.group(1))


def _parse_float_from_output(pattern: str, raw_output: str) -> float | None:
    match = re.search(pattern, raw_output)
    if match is None:
        return None
    return float(match.group(1))


def _list_fauxpy_report_dirs(worktree: Path) -> dict[Path, Path]:
    parent = worktree.parent
    if not parent.exists():
        return {}
    return {
        path.resolve(): path for path in parent.glob("FauxPyReport_*") if path.is_dir()
    }


def _find_new_fauxpy_report_dir(
    before: dict[Path, Path], after: dict[Path, Path]
) -> Path | None:
    new_paths = [path for key, path in after.items() if key not in before]
    candidates = new_paths or list(after.values())
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def _query_mbfl_validation_metadata(report_dir: Path | None) -> dict[str, int | str]:
    if report_dir is None:
        return {}

    db_path = report_dir / "fauxpy.db"
    if not db_path.exists():
        return {"fauxpy_report_dir": str(report_dir)}

    metadata: dict[str, int | str] = {"fauxpy_report_dir": str(report_dir)}
    try:
        with sqlite3.connect(str(db_path)) as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM MutantInfo")
            metadata["mutants_validated"] = int(cursor.fetchone()[0])
            cursor.execute("SELECT COUNT(*) FROM MutantInfo WHERE Timeout = 1")
            metadata["mutants_timed_out"] = int(cursor.fetchone()[0])
            cursor.execute("SELECT COUNT(*) FROM MutantInfo WHERE HasMissingTests = 1")
            metadata["mutants_with_missing_tests"] = int(cursor.fetchone()[0])
    except sqlite3.Error:
        return metadata

    return metadata


def extract_mbfl_tracking_metadata(
    raw_output: str, report_dir: Path | None = None
) -> dict[str, int | float | str]:
    """Extract MBFL cost-control metadata from FauxPy output and report DB."""
    metadata: dict[str, int | float | str] = {}
    output_patterns = {
        "candidate_mutation_locations": r"Candidate mutation locations:\s+(\d+)",
        "selected_mutation_locations": r"Selected mutation locations:\s+(\d+)",
        "mutants_generated": r"Total generated mutants:\s+(\d+)",
        "mutants_validated": r"Mutants selected for validation:\s+(\d+)",
    }

    for key, pattern in output_patterns.items():
        value = _parse_int_from_output(pattern, raw_output)
        if value is not None:
            metadata[key] = value

    if "mutants_validated" not in metadata:
        running_count = _parse_int_from_output(r"Running\s+(\d+)\s+Mutants", raw_output)
        if running_count is not None:
            metadata["mutants_validated"] = running_count

    generated_counts = [
        int(match)
        for match in re.findall(r"Number of generated mutants:\s+(\d+)", raw_output)
    ]
    if generated_counts and "mutants_generated" not in metadata:
        metadata["mutants_generated"] = sum(generated_counts)

    time_patterns = {
        "mutation_generation_time_seconds": r"Mutation generation time:\s+([0-9]+(?:\.[0-9]+)?)",
        "mutant_validation_time_seconds": r"Mutant validation time:\s+([0-9]+(?:\.[0-9]+)?)",
    }
    for key, pattern in time_patterns.items():
        value = _parse_float_from_output(pattern, raw_output)
        if value is not None:
            metadata[key] = value

    for key, value in _query_mbfl_validation_metadata(report_dir).items():
        metadata.setdefault(key, value)
    return metadata


def _translate_unittest_target(target: str) -> str:
    parts = target.split(".")
    selector_start = None

    for index, part in enumerate(parts):
        if part[:1].isupper():
            selector_start = index
            break

    if selector_start is None and len(parts) > 2 and parts[-1].startswith("test"):
        selector_start = len(parts) - 1

    module_parts = parts if selector_start is None else parts[:selector_start]
    selector_parts = [] if selector_start is None else parts[selector_start:]

    module = "/".join(module_parts) + ".py"
    if not selector_parts:
        return module

    return module + "::" + "::".join(selector_parts)


def _unittest_targets(parts: list[str]) -> list[str]:
    targets: list[str] = []
    skip_next = False
    options_with_values = {"-k", "--pattern"}

    for part in parts:
        if skip_next:
            skip_next = False
            continue
        if part in options_with_values:
            skip_next = True
            continue
        if part.startswith("-"):
            continue
        if part == "discover":
            raise ConfigurationError(
                "FauxPy localization does not support unittest discover commands."
            )

        targets.append(_translate_unittest_target(part))

    return targets


def load_pytest_targets(run_test_script: Path) -> list[str]:
    """Return pytest targets declared by a BugsInPy ``run_test.sh`` script.

    The parser accepts direct ``pytest`` commands, ``python -m pytest`` commands,
    and targeted ``python -m unittest`` commands that pytest can execute after
    translation to node IDs. It skips comments and blank lines, and raises
    ``ConfigurationError`` when the script is missing, contains unsupported
    commands, or has no runnable pytest targets.
    """
    if not run_test_script.exists():
        raise ConfigurationError(f"No BugsInPy test script found at {run_test_script}")

    targets: list[str] = []
    for raw_line in run_test_script.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        # split each command like shell
        parts = shlex.split(line)

        if not parts:
            continue
        # direct pytest calls (pytest tests/test.py tests/test_test.py)
        if parts[0] == "pytest":
            targets.extend(parts[1:])
            continue
        # python -m pytest style calls
        if len(parts) >= 3 and parts[1:3] == ["-m", "pytest"]:
            targets.extend(parts[3:])
            continue
        # python -m unittest style calls
        if len(parts) >= 3 and parts[1:3] == ["-m", "unittest"]:
            targets.extend(_unittest_targets(parts[3:]))
            continue

        raise ConfigurationError(
            "FauxPy localization currently supports BugsInPy run_test.sh lines "
            "that invoke pytest directly or targeted unittest commands. "
            f"Unsupported line: {line}"
        )

    if not targets:
        raise ConfigurationError(f"No pytest targets found in {run_test_script}")

    return targets


def extract_pytest_node_ids(test_targets: list[str]) -> list[str]:
    """Filter out pytest CLI flags (e.g. -q, -s), keeping only test node IDs."""
    return [
        test_target for test_target in test_targets if not test_target.startswith("-")
    ]


@dataclass(frozen=True)
class FauxPyConfig:
    """Configuration for one FauxPy localization run.

    The config describes the fault-localization family, source root, granularity,
    test selection, and metric to expose as the primary ranking. Validation keeps
    unsupported combinations out of the toolchain before any subprocess runs.
    """

    family: str = "sbfl"  # sbfl | mbfl
    granularity: str = "statement"  # statement | function
    src: str = "."
    exclude: list[str] = field(default_factory=list)
    test_targets: list[str] = field(default_factory=list)
    failing_tests: list[str] = field(default_factory=list)
    top_n: int | None = None
    # MBFL-only knobs
    mutation_strategy: str | None = None
    mutation_budget: int | None = None
    mutation_seed: int = 0
    # Metric selection
    metric: str | None = None

    def __post_init__(self) -> None:
        """Validate FauxPy options and reject unsupported combinations early."""
        if self.family not in {"sbfl", "mbfl"}:
            raise ConfigurationError(
                "Currently the FauxPy integration supports only SBFL and MBFL."
            )
        if self.granularity not in {"statement", "function"}:
            raise ConfigurationError(
                "Currently the FauxPy integration only supports statement level and function level granularity"
            )
        if (
            self.mutation_strategy is not None or self.mutation_budget is not None
        ) and self.family != "mbfl":
            raise ConfigurationError("Mutation selection options are MBFL only.")
        if self.mutation_strategy is not None:
            if self.mutation_strategy != "random":
                raise ConfigurationError(
                    "Currently the FauxPy integration supports only the random mutation selection strategy."
                )
            if self.mutation_budget is None:
                raise ConfigurationError(
                    "FauxPy mutation selection requires a positive mutation budget."
                )
        if self.mutation_budget is not None:
            if not isinstance(self.mutation_budget, int) or self.mutation_budget <= 0:
                raise ConfigurationError(
                    "FauxPy mutation budget must be a positive integer."
                )
            if self.mutation_strategy is None:
                raise ConfigurationError(
                    "FauxPy mutation budget requires a mutation strategy."
                )
        if not isinstance(self.mutation_seed, int):
            raise ConfigurationError("FauxPy mutation seed must be an integer.")
        if self.metric is None:
            object.__setattr__(
                self,
                "metric",
                "metallaxis" if self.family == "mbfl" else "ochiai",
            )
        elif not isinstance(self.metric, str) or not self.metric.strip():
            raise ConfigurationError("FauxPy metric must be a non-empty string.")
        if not isinstance(self.src, str) or not self.src.strip():
            raise ConfigurationError("FauxPy src must be a non-empty string.")
        if self.top_n is not None:
            if not isinstance(self.top_n, int) or self.top_n <= 0:
                raise ConfigurationError(
                    "FauxPy top_n must be a positive integer or None."
                )

        _validate_string_list("test_targets", self.test_targets)
        _validate_string_list("failing_tests", self.failing_tests)


class DockerCommandRunner(Protocol):
    """Protocol for benchmark toolchains that execute commands in a checkout."""

    def run_command(
        self,
        args: list[str],
        *,
        cwd: Path | None = None,
        check: bool = True,
        capture_output: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        """Run ``args`` in the benchmark environment and return the completed process."""
        ...


class FauxPyToolchain:
    """Run FauxPy inside a prepared benchmark checkout.

    The toolchain installs FauxPy into the checkout virtual environment when
    needed, executes pytest with FauxPy options, parses all emitted metric
    tables, and returns a structured ``LocalizationResult`` for the configured
    primary metric.
    """

    def __init__(self, runner: DockerCommandRunner) -> None:
        """Create a toolchain using ``runner`` for all subprocess execution."""
        self._runner = runner

    def localize(
        self, config: FauxPyConfig, checkout: CheckoutResult
    ) -> LocalizationResult:
        """Run FauxPy for ``checkout`` and return ranked locations for ``config.metric``.

        The result metadata includes the raw command output, the selected score
        formula, the FauxPy run options, and ``all_metrics`` containing every
        parsed metric table for later consumers.
        """
        # Use a relative interpreter path because BugsInPy creates the venv in
        # its executor container; absolute venv symlinks can look broken here.
        python = Path("env") / "bin" / "python"
        host_python = checkout.worktree / python
        if not host_python.exists() and not host_python.is_symlink():
            raise ConfigurationError(
                f"No prepared virtual environment found at {host_python}. "
                "Run `python -m apr_framework bugsinpy compile "
                f"{checkout.bug.project} {checkout.bug.bug_id}` first."
            )

        self._ensure_patched_fauxpy_installed(python, checkout.worktree)

        fauxpy_command = self._build_fauxpy_command(python, config)
        before_report_dirs = _list_fauxpy_report_dirs(checkout.worktree)

        completed = self._runner.run_command(
            fauxpy_command,
            cwd=checkout.worktree,
            check=False,
            capture_output=True,
        )
        raw_output = _completed_output(completed)
        report_dir = _find_new_fauxpy_report_dir(
            before_report_dirs,
            _list_fauxpy_report_dirs(checkout.worktree),
        )

        if completed.returncode not in {0, 1}:
            raise ConfigurationError(
                f"FauxPy localization command failed. {raw_output}".strip()
            )

        all_metrics = parse_fauxpy_output(raw_output, metric_filter=None)
        formula = _resolve_metric_name(all_metrics, config.metric)
        if formula is None:
            available_metrics = ", ".join(sorted(all_metrics)) or "none"
            raise ConfigurationError(
                f"Metric '{config.metric}' was not emitted by FauxPy. "
                f"Available metrics: {available_metrics}. "
                "If you requested Jaccard or SBI, make sure the prepared checkout uses "
                "the framework's patched FauxPy installation."
            )

        ranked_locations = parse_fauxpy_output(
            raw_output,
            metric_filter=config.metric,
            top_n=config.top_n,
        )

        metadata = {
            "family": config.family,
            "src": config.src,
            "test_targets": list(config.test_targets),
            "score_formula": formula,
            "all_metrics": all_metrics,
            "raw_output": raw_output,
            "returncode": completed.returncode,
        }
        if config.family == "mbfl":
            metadata.update(
                {
                    "mutation_strategy": config.mutation_strategy,
                    "mutation_budget": config.mutation_budget,
                    "mutation_seed": config.mutation_seed,
                }
            )
            metadata.update(extract_mbfl_tracking_metadata(raw_output, report_dir))

        return LocalizationResult(
            bug=checkout.bug,
            backend="fauxpy",
            ranked_locations=ranked_locations,
            metadata=metadata,
        )

    def _ensure_patched_fauxpy_installed(self, python: Path, cwd: Path) -> None:
        self._ensure_fauxpy_installed(python, cwd)
        self._apply_fauxpy_sbfl_metric_patch(python, cwd)
        self._apply_fauxpy_mbfl_selection_patch(python, cwd)

    def _ensure_fauxpy_installed(self, python: Path, cwd: Path) -> None:
        show = self._runner.run_command(
            [str(python), "-m", "pip", "show", "fauxpy"],
            cwd=cwd,
            check=False,
            capture_output=True,
        )
        if show.returncode == 0:
            return

        self._upgrade_fauxpy_build_tools(python, cwd)

        install = self._runner.run_command(
            [str(python), "-m", "pip", "install", FAUXPY_INSTALL_REQUIREMENT],
            cwd=cwd,
            check=False,
            capture_output=True,
        )
        if install.returncode != 0:
            raise ConfigurationError(
                "FauxPy is not installed in the project environment and installation "
                f"failed. {_completed_output(install)}".strip()
            )

    def _apply_fauxpy_sbfl_metric_patch(self, python: Path, cwd: Path) -> None:
        patch = self._runner.run_command(
            [str(python), "-c", _FAUXPY_SBFL_METRICS_PATCH_SCRIPT],
            cwd=cwd,
            check=False,
            capture_output=True,
        )
        if patch.returncode != 0:
            raise ConfigurationError(
                "FauxPy is installed, but the framework could not apply the "
                f"custom SBFL metric patch. {_completed_output(patch)}".strip()
            )

    def _apply_fauxpy_mbfl_selection_patch(self, python: Path, cwd: Path) -> None:
        patch = self._runner.run_command(
            [str(python), "-c", _FAUXPY_MBFL_SELECTION_PATCH_SCRIPT],
            cwd=cwd,
            check=False,
            capture_output=True,
        )
        if patch.returncode != 0:
            raise ConfigurationError(
                "FauxPy is installed, but the framework could not apply the "
                f"MBFL selection patch. {_completed_output(patch)}".strip()
            )

    def _upgrade_fauxpy_build_tools(self, python: Path, cwd: Path) -> None:
        upgrade = self._runner.run_command(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--upgrade",
                "pip<25.1",
                "setuptools",
                "wheel",
                "packaging",
            ],
            cwd=cwd,
            check=False,
            capture_output=True,
        )
        if upgrade.returncode != 0:
            raise ConfigurationError(
                "FauxPy is not installed in the project environment and the "
                "framework could not upgrade the environment build tooling. "
                f"{_completed_output(upgrade)}".strip()
            )

    def _build_fauxpy_command(self, python: Path, config: FauxPyConfig):
        """
        Helper function to build FauxPy commands from FauxPy-Config object
        """
        cmd = [
            str(python),
            "-m",
            "pytest",
            *config.test_targets,
            "--src",
            config.src,
            "--family",
            config.family,
            "--granularity",
            config.granularity,
        ]
        if config.top_n is not None:
            cmd += ["--top-n", str(config.top_n)]
        if config.failing_tests:
            cmd += ["--failing-list", "[" + ",".join(config.failing_tests) + "]"]
        if config.family == "mbfl" and config.mutation_strategy is not None:
            cmd += [
                "--mutation-selection",
                config.mutation_strategy,
                "--mutation-budget",
                str(config.mutation_budget),
                "--mutation-seed",
                str(config.mutation_seed),
            ]
        for ex in config.exclude:
            cmd += ["--exclude", ex]
        return cmd


class FauxPyLocalizer(FaultLocalizer):
    """Fault-localizer adapter that delegates FauxPy execution to a toolchain."""

    def __init__(self, config: FauxPyConfig, toolchain: FauxPyToolchain) -> None:
        """Create a localizer with a fixed FauxPy config and execution toolchain."""
        self._config = config
        self._toolchain = toolchain

    @property
    def name(self) -> str:
        """Return the stable backend name used in localization results."""
        return "fauxpy"

    def localize(
        self,
        bug: BugIdentifier,
        checkout: CheckoutResult,
        test_result: TestRunResult | None = None,
    ) -> LocalizationResult:
        """Localize ``bug`` in ``checkout`` using the configured FauxPy metric.

        ``test_result`` is accepted to match the framework interface; FauxPy
        derives its test selection from ``FauxPyConfig`` and the prepared
        checkout instead.
        """
        return self._toolchain.localize(self._config, checkout)


@overload
def parse_fauxpy_output(
    raw_output: str,
    *,
    metric_filter: None = None,
    top_n: int | None = None,
) -> dict[str, list[RankedLocation]]: ...


@overload
def parse_fauxpy_output(
    raw_output: str,
    *,
    metric_filter: str,
    top_n: int | None = None,
) -> list[RankedLocation]: ...


def parse_fauxpy_output(
    raw_output: str,
    *,
    metric_filter: str | None = None,
    top_n: int | None = None,
) -> dict[str, list[RankedLocation]] | list[RankedLocation]:
    """Parse FauxPy metric tables from pytest output.

    FauxPy emits one ASCII table per scoring metric. When ``metric_filter`` is
    ``None``, this function returns every table as ``{metric_name: rows}``.
    When ``metric_filter`` is set, it returns only that metric's ranked rows.
    Statement rows use ``File | Line | Score`` and function rows use
    ``File | Function | Line | Score``.
    """
    metric_tables: dict[str, list[RankedLocation]] = {}
    current_metric: str | None = None
    current_rows: list[RankedLocation] | None = None
    formula_pattern = re.compile(r"Scores for (?P<formula>.+?)\s+\|")
    row_pattern = re.compile(
        r"^(?P<file>.+?)\s+\|"
        r"(?:\s+(?P<function>.+?)\s+\|)?"
        r"\s+(?P<line>\d+)(?:-(?P<end_line>\d+))?\s+\|"
        r"\s+(?P<score>[+-]?\d+(?:\.\d+)?)\s*$"
    )

    for raw_line in raw_output.splitlines():
        line = raw_line.rstrip()

        formula_match = formula_pattern.search(line)
        if formula_match:
            current_metric = formula_match.group("formula").strip()
            current_rows = metric_tables.setdefault(current_metric, [])
            continue

        if current_metric is None or current_rows is None:
            continue

        if (
            not line.strip()
            or line.lstrip().startswith("-")
            or line.strip().startswith("|")
        ):
            continue

        if line.strip().startswith("File"):
            continue

        row_match = row_pattern.match(line)
        if row_match is None:
            continue

        file_path = row_match.group("file").strip()
        function = row_match.group("function")
        function = function.strip() if function is not None else None
        line_number = int(row_match.group("line"))
        end_line = row_match.group("end_line")
        score = float(row_match.group("score"))
        current_rows.append(
            RankedLocation(
                rank=len(current_rows) + 1,
                file_path=file_path,
                location=(
                    f"{file_path}:{function}:{line_number}"
                    if function
                    else f"{file_path}:{line_number}"
                ),
                score=score,
                line=line_number,
                end_line=int(end_line) if end_line is not None else None,
                function=function,
                raw_location=line.strip(),
                metadata={"score_formula": current_metric},
            )
        )

    if metric_filter is None:
        if top_n is None:
            return metric_tables
        return {metric: rows[:top_n] for metric, rows in metric_tables.items()}

    selected_metric = _resolve_metric_name(metric_tables, metric_filter)
    if selected_metric is None:
        return []
    rows = metric_tables[selected_metric]
    if top_n is not None:
        return rows[:top_n]
    return rows


def _resolve_metric_name(
    metric_tables: dict[str, list[RankedLocation]], metric_filter: str
) -> str | None:
    normalized_filter = metric_filter.strip().casefold()
    for metric in metric_tables:
        if metric.casefold() == normalized_filter:
            return metric
    return None
