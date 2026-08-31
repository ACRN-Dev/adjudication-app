"""Reconcile Postgres enum types with the labels the SQLAlchemy models expect.

Base.metadata.create_all() only ever CREATES missing objects. It never adds a label to
an enum type that already exists, exactly as it never adds a column to a table that
already exists. So an enum member added to a model after production's tables were first
created is simply absent from Postgres, and the first statement naming it fails:

    invalid input value for enum reviewerrole: "REVIEWER_C"

That is how Reviewer C reached production without REVIEWER_C ever reaching the
reviewerrole type -- 20260817_06_sprint1_chair_and_reviewer_c.sql added the columns but
nothing ever taught Postgres the new role.

Postgres refuses to USE a new enum label inside the transaction that added it:

    ERROR: unsafe use of new value "REVIEWER_C" of enum type reviewerrole
    HINT:  New enum values must be committed before they can be used.

so this has to run, and commit, BEFORE the migrations that reference the new labels.
Each ALTER TYPE is issued on an autocommitting connection for that reason.

Reconciliation is keyed on the type a column ACTUALLY has in the database, not on the
type name the model declares. The two diverge as soon as a migration retypes a column:
20260826_09 moves diagnosis and final_diagnosis from diagnosiscode onto diagnosis_code_v2,
and keying off the model name would keep topping up the abandoned type while the live one
silently fell behind.

Adding a label is additive and non-destructive: existing rows keep their value, and a new
label is appended to the end of the sort order. Labels are never removed -- dropping one
would break whatever rows still hold it -- so a label present in the database but absent
from the models is left alone and reported to the caller.
"""
from collections import defaultdict

from sqlalchemy import Enum as SAEnumType
from sqlalchemy import text


def model_enum_columns(metadata):
    """[(table_name, column_name, labels), ...] for every native-enum column."""
    found = []
    for table in metadata.sorted_tables:
        for column in table.columns:
            column_type = column.type
            if not isinstance(column_type, SAEnumType):
                continue
            if not column_type.native_enum or not column_type.name:
                continue
            # Read the labels off the SQLAlchemy Enum, not the Python enum: SQLAlchemy
            # persists member NAMES and skips aliases (DiagnosisCode.PREECLAMPSIA is an
            # alias of PE), so its own .enums list is the only faithful account of what
            # it will actually write.
            found.append((table.name, column.name, list(column_type.enums)))
    return found


def _live_column_types(conn):
    """(table, column) -> Postgres type name, for enum-typed columns in this schema."""
    rows = conn.execute(text(
        "SELECT c.relname, a.attname, t.typname "
        "FROM pg_attribute a "
        "JOIN pg_class c ON c.oid = a.attrelid "
        "JOIN pg_namespace n ON n.oid = c.relnamespace "
        "JOIN pg_type t ON t.oid = a.atttypid "
        "WHERE n.nspname = current_schema() AND c.relkind = 'r' "
        "AND a.attnum > 0 AND NOT a.attisdropped AND t.typtype = 'e'"
    ))
    return {(table, column): type_name for table, column, type_name in rows}


def _labels_by_type(conn):
    """Postgres enum type name -> set of its current labels."""
    rows = conn.execute(text(
        "SELECT t.typname, e.enumlabel FROM pg_enum e "
        "JOIN pg_type t ON t.oid = e.enumtypid "
        "JOIN pg_namespace n ON n.oid = t.typnamespace "
        "WHERE n.nspname = current_schema()"
    ))
    labels = defaultdict(set)
    for type_name, label in rows:
        labels[type_name].add(label)
    return labels


def sync_enum_labels(engine, metadata):
    """Add any missing labels to enum types that already exist in the database.

    Returns (added, extra):
      added -- [(type_name, label), ...] labels this call added
      extra -- [(type_name, label), ...] labels in the database that no model declares
    Enum types that do not exist yet are skipped: create_all() builds those complete.
    """
    added, extra = [], []
    columns = model_enum_columns(metadata)
    if not columns:
        return added, extra

    preparer = engine.dialect.identifier_preparer
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        live_types = _live_column_types(conn)
        present = _labels_by_type(conn)

        # Several columns can share one enum type; union what they each expect.
        wanted = defaultdict(list)
        for table_name, column_name, labels in columns:
            type_name = live_types.get((table_name, column_name))
            if type_name is None:
                continue  # table or column not in this database yet
            for label in labels:
                if label not in wanted[type_name]:
                    wanted[type_name].append(label)

        for type_name, labels in sorted(wanted.items()):
            have = present.get(type_name, set())
            if not have:
                continue
            quoted_type = preparer.quote(type_name)
            for label in labels:
                if label in have:
                    continue
                # ALTER TYPE ... ADD VALUE takes a literal, not a bind parameter.
                literal = "'" + label.replace("'", "''") + "'"
                conn.execute(
                    text(f"ALTER TYPE {quoted_type} ADD VALUE IF NOT EXISTS {literal}")
                )
                added.append((type_name, label))
            extra.extend(sorted((type_name, label) for label in have - set(labels)))

    return added, extra
