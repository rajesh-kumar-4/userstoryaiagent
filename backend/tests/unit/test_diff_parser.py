from app.domain.models import ChangeArea, ChangeType
from app.infrastructure.git.diff_parser import parse_name_status, parse_unified_hunks

PATCH = """diff --git a/src/A.java b/src/A.java
index 1111111..2222222 100644
--- a/src/A.java
+++ b/src/A.java
@@ -1,2 +1,3 @@
-old
+new
+more
+extra
diff --git a/new/name.txt b/new/name.txt
new file mode 100644
--- /dev/null
+++ b/new/name.txt
@@ -0,0 +1 @@
+hello
"""


def test_hunks_pair_deleted_and_added_lines_as_modified():
    stats = parse_unified_hunks(PATCH)

    assert stats["src/A.java"].modified == 1
    assert stats["src/A.java"].added == 2
    assert stats["src/A.java"].deleted == 0
    assert stats["new/name.txt"].added == 1


def test_name_status_parses_rename_and_add():
    output = "M\0src/A.java\0A\0new/name.txt\0R100\0old.txt\0renamed.txt\0"
    files = parse_name_status(output, parse_unified_hunks(PATCH), ChangeArea.COMPARISON)

    by_path = {item.path: item for item in files}
    assert by_path["src/A.java"].change_type is ChangeType.MODIFIED
    assert by_path["src/A.java"].modified_lines == 1
    assert by_path["new/name.txt"].change_type is ChangeType.ADDED
    assert by_path["renamed.txt"].change_type is ChangeType.RENAMED
    assert by_path["renamed.txt"].old_path == "old.txt"
