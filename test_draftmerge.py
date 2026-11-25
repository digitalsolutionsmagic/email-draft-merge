import csv
import tempfile
import unittest
from pathlib import Path

import draftmerge as dm


def read(path: Path):
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


class UnitTests(unittest.TestCase):
    def test_render_ok(self):
        out, missing = dm.render("Hi {{First Name}} at {{company}}",
                                 {"first name": "Ana", "company": "Acme"})
        self.assertEqual((out, missing), ("Hi Ana at Acme", []))

    def test_render_missing_and_alias(self):
        out, missing = dm.render("Hi {{first_name}}", {"first name": ""})
        self.assertEqual(out, "Hi {{first_name}}")
        self.assertEqual(missing, ["first_name"])

    def test_parse_template(self):
        self.assertEqual(dm.parse_template("\nSubject: Hello\n\nBody line\n"),
                         ("Hello", "Body line"))
        with self.assertRaises(dm.MergeError):
            dm.parse_template("Hello\nBody")
        with self.assertRaises(dm.MergeError):
            dm.parse_template("Subject:   \nBody")


class EndToEnd(unittest.TestCase):
    TEMPLATE = ("Subject: Quick question, {{First Name}}\n\n"
                "Hi {{First Name}},\n\nI saw {{Company}} recently: {{Recent Post}}.\n\n"
                "Thanks,\nSender\n")
    LEADS = ("First Name,Company,Email,Recent Post\n"
             "Ana,Acme,ana@acme-example.com,Launched X\n"
             "Ben,Beta,,Wrote Y\n"
             "Cy,Cee,cy@cee-example.com,\n"
             "Dee,Dee Co,ana@acme-example.com,Posted Z\n"
             "Eli,Eli Co,not-an-email,Posted Q\n")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.csv = self.dir / "leads.csv"
        self.tpl = self.dir / "t.txt"
        self.out = self.dir / "out.csv"
        self.csv.write_text(self.LEADS, encoding="utf-8")
        self.tpl.write_text(self.TEMPLATE, encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_full_run(self):
        code = dm.main([str(self.csv), str(self.tpl), "-o", str(self.out)])
        self.assertEqual(code, 0)
        rows = read(self.out)
        self.assertEqual([r["status"] for r in rows],
                         ["drafted", "skipped", "skipped", "skipped", "skipped"])
        self.assertEqual(rows[0]["subject"], "Quick question, Ana")
        self.assertIn("Launched X", rows[0]["body"])
        self.assertEqual(rows[1]["reason"], "missing email")
        self.assertEqual(rows[2]["reason"], "missing value for: Recent Post")
        self.assertEqual(rows[3]["reason"], "duplicate email")
        self.assertEqual(rows[4]["reason"], "invalid email")

    def test_refuses_overwrite_without_force(self):
        args = [str(self.csv), str(self.tpl), "-o", str(self.out)]
        self.assertEqual(dm.main(args), 0)
        self.assertEqual(dm.main(args), 2)
        self.assertEqual(dm.main(args + ["--force"]), 0)

    def test_errors(self):
        self.assertEqual(dm.main([str(self.dir / "nope.csv"), str(self.tpl)]), 2)
        self.assertEqual(dm.main([str(self.csv), str(self.dir / "nope.txt")]), 2)
        bad = self.dir / "bad.txt"
        bad.write_text("no subject here\n", encoding="utf-8")
        self.assertEqual(dm.main([str(self.csv), str(bad), "-o", str(self.out)]), 2)
        noemail = self.dir / "noemail.csv"
        noemail.write_text("Name,Company\nA,B\n", encoding="utf-8")
        self.assertEqual(dm.main([str(noemail), str(self.tpl), "-o", str(self.out)]), 2)


if __name__ == "__main__":
    unittest.main()
