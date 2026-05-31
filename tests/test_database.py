import unittest

from app.database import split_sql_statements


class DatabaseSchemaTest(unittest.TestCase):
    def test_split_sql_statements_removes_empty_fragments(self):
        statements = split_sql_statements("CREATE TABLE one (id int); ; CREATE INDEX x ON one(id);")

        self.assertEqual(len(statements), 2)
        self.assertEqual(statements[0], "CREATE TABLE one (id int)")
        self.assertEqual(statements[1], "CREATE INDEX x ON one(id)")


if __name__ == "__main__":
    unittest.main()
