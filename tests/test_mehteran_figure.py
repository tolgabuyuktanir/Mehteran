"""Figures in results (mehteran/common/figure.py): a "figure" code block with JSON data, drawn as SVG by Mehteran.

The HTML export and the reader (mehteran/ui/markdown.js) must draw the same figure; the parity test runs the
JavaScript with Node.js when it is installed.
"""

import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

from mehteran import tables
from mehteran.common import export, figure

ROOT = Path(__file__).resolve().parent.parent

PLOT = {"type": "plot", "alt": "A parabola and a line", "caption": "Figure 1", "x": [-4, 6], "y": [-5, 7], "grid": 1,
        "items": [{"fn": "(x - 1)^2 - 4", "label": "y = f(x)"}, {"fn": "2x - 3", "dash": True},
                  {"points": [[-1, 0, "A"], [3, 0, "B"]]}, {"text": "P", "at": [1, -4.5]}]}
GEOMETRY = {"alt": "Right triangle ABC", "axes": False, "x": [-1, 9], "y": [-1, 7],
            "items": [{"line": [[0, 0], [8, 0], [0, 6]], "closed": True, "fill": True, "color": 2},
                      {"points": [[0, 0, "A"], [8, 0, "B"], [0, 6, "C"]]}, {"circle": [0, 0, 1.5], "label": "r"}]}
BAR = {"type": "bar", "alt": "Books read", "ylabel": "Books", "xlabel": "Month",
       "bars": [["Jan", 12], ["Feb", 7.5], ["Mar", 0], ["Apr", 15]]}
SPECS = [PLOT, GEOMETRY, BAR,
         {"alt": "Asymptotes", "x": [-5, 5], "y": [-6, 6], "items": [{"fn": "1/(x - 1) + tan(x)"}, {"fn": "sqrt(x) + ln(x)"},
                                                                     {"fn": "(-x)^0.5", "domain": [-4, 0]}]},
         {"alt": "No axes at 0", "x": [2, 12], "y": [10, 40], "grid": 0, "items": [{"fn": "3x + 4", "label": "cost"}]},
         {"alt": "Dense ticks", "x": [-20, 20], "y": [-0.5, 0.5], "items": [{"fn": "0.4sin(pi x / 10)"}]}]


def numbers_equal(a, b) -> bool:
    """Two trees are equal, numbers within 0.011 (JavaScript and C may differ in the last digit of sin or exp)."""
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(numbers_equal(x, y) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(numbers_equal(a[k], b[k]) for k in a)
    if isinstance(a, str) and isinstance(b, str):
        pa, pb = re.split(r"(-?\d+(?:\.\d+)?)", a), re.split(r"(-?\d+(?:\.\d+)?)", b)
        if len(pa) != len(pb):
            return False
        for n, (x, y) in enumerate(zip(pa, pb)):
            if n % 2 and abs(float(x) - float(y)) > 0.011 or not n % 2 and x != y:
                return False
        return True
    return a == b


class Figures(unittest.TestCase):
    def test_a_valid_figure_is_svg_with_its_description(self):
        page = figure.svg(json.dumps(PLOT))
        self.assertTrue(page.startswith('<svg xmlns="http://www.w3.org/2000/svg" class="fig"'))
        self.assertIn('aria-label="A parabola and a line"', page)
        self.assertIn("<title>A parabola and a line</title>", page)
        self.assertEqual(page.count('class="fig-dot fig-d0"'), 2)
        self.assertIn("fig-line fig-c1 fig-dash", page)
        self.assertIn(">y = f(x)</text>", page)

    def test_label_steps_skip_odd_ticks(self):
        page = figure.svg(json.dumps({"alt": "a", "x": [-10, 10], "y": [-10, 10], "grid": 1}))
        labels = re.findall(r'class="fig-tick"[^>]*>(-?\d+)<', page)
        self.assertIn("2", labels)
        self.assertNotIn("1", labels)
        self.assertNotIn("-3", labels)

    def test_invalid_figures_are_refused(self):
        for bad in ["not json", "[]", "{}", '{"alt": ""}', json.dumps({**PLOT, "x": [3, 1]}),
                    json.dumps({**PLOT, "type": "pie"}), json.dumps({**PLOT, "items": [{"fn": "__import__('os')"}]}),
                    json.dumps({**PLOT, "items": [{"fn": "x + y"}]}), json.dumps({**PLOT, "items": [{"fn": "2 ** 3 ;"}]}),
                    json.dumps({**PLOT, "items": [{"line": [[0, 0]]}]}), json.dumps({**PLOT, "items": [{"href": "x"}]}),
                    json.dumps({**PLOT, "items": [{"points": [[0, 0]], "color": 7}]}),
                    json.dumps({**PLOT, "items": [{"points": [[0, 0]] * 2001}]}),
                    json.dumps({**PLOT, "x": [0, 1e9]}), '{"alt": "a", "x": [0, NaN], "y": [0, 1]}',
                    json.dumps({**BAR, "bars": []}), json.dumps({**PLOT, "caption": "c" * 201}), json.dumps({**PLOT, "xlabel": "x" * 61})]:
            with self.subTest(bad=bad[:60]):
                self.assertIsNone(figure.svg(bad))

    def test_long_axis_labels_are_allowed(self):
        self.assertIsNotNone(figure.svg(json.dumps({**PLOT, "xlabel": "Advertising spending (hundreds of dollars)"})))

    def test_text_is_escaped(self):
        page = figure.svg(json.dumps({"alt": 'a "<b>"', "x": [0, 1], "y": [0, 1],
                                      "items": [{"text": "<script>alert(1)</script>", "at": [0.5, 0.5]}]}))
        self.assertNotIn("<script>", page)
        self.assertNotIn("<b>", page)
        self.assertIn("&lt;script&gt;", page)
        self.assertIn('aria-label="a &quot;&lt;b&gt;&quot;"', page)

    def test_functions(self):
        f = figure.compile_fn("2x^2 - 3(x + 1) + sqrt(abs(x)) - ln(e) + log(100) - pi + -x^2")
        self.assertAlmostEqual(f(2.0), 8 - 9 + 2 ** 0.5 - 1 + 2 - 3.141592653589793 - 4)
        self.assertNotEqual(figure.compile_fn("sqrt(x)")(-1), figure.compile_fn("sqrt(x)")(-1))  # nan
        self.assertNotEqual(figure.compile_fn("1/x")(0), figure.compile_fn("1/x")(0))
        self.assertAlmostEqual(figure.compile_fn("x²−1")(3), 8)

    def test_numbers_round_as_javascript(self):
        self.assertEqual([figure.num(v) for v in (0.125, -0.125, 2.5, -0.001, 10.0, 1.005, 3.14159)],
                         ["0.13", "-0.13", "2.5", "0", "10", "1", "3.14"])

    def test_export_draws_figures_and_choices(self):
        md = (f"# Set\n\n## Question 1\n\nWhich?\n\n```figure\n{json.dumps(PLOT)}\n```\n\nA) 1\nB) 2\nC) 3\nD) 4\n\n"
              "```figure\n{broken\n```\n")
        page = tables.to_html(md, "Set", "en")
        self.assertIn('<figure class="fig-box"><svg', page)
        self.assertIn("<figcaption>Figure 1</figcaption>", page)
        self.assertIn('<ol class="choices"><li><span class="letter">A</span><span>1</span></li>', page)
        self.assertIn("<pre><code>{broken</code></pre>", page)  # not a figure: shown as code
        self.assertIn(".fig .fig-c0", page)

    def test_lines_that_are_not_choices_stay_a_paragraph(self):
        for text in ("A) one\nC) three", "A) only one", "A) one\nB) two\nplain"):
            page = export.to_html(text, "T", "en")
            self.assertNotIn('class="choices"', page)

    def test_word_and_pdf_get_the_description(self):
        md = f"Before\n\n```figure\n{json.dumps(BAR)}\n```\n\n```figure\nnot a figure\n```\n"
        self.assertEqual(figure.as_text(md), "Before\n\n*Books read*\n\n```figure\nnot a figure\n```\n")


@unittest.skipUnless(shutil.which("node"), "Node.js is not installed")
class SameAsTheReader(unittest.TestCase):
    def test_javascript_draws_the_same_figures(self):
        script = ("const vm = require('vm'), fs = require('fs'); const ctx = {};"
                  f"vm.runInNewContext(fs.readFileSync({json.dumps(str(ROOT / 'mehteran/ui/markdown.js'))}, 'utf8'), ctx);"
                  "const specs = JSON.parse(fs.readFileSync(0, 'utf8'));"
                  "console.log(JSON.stringify(specs.map((s) => { try { return ctx.Markdown.figure(s); } catch (e) { return null; } })));")
        bad = [{**PLOT, "items": [{"fn": "x +* 2"}]}, {**BAR, "bars": [["a", True]]}, {**PLOT, "axes": "yes"}]
        specs = SPECS + bad
        out = subprocess.run(["node", "-e", script], input=json.dumps(specs), capture_output=True, text=True, timeout=60, check=True)
        drawn = json.loads(out.stdout)
        for spec, js in zip(specs, drawn):
            with self.subTest(alt=spec["alt"]):
                try:
                    py = json.loads(json.dumps(figure.tree(spec)))
                except ValueError:
                    py = None
                if py is None or js is None:
                    self.assertEqual(py, js)
                else:
                    self.assertTrue(numbers_equal(py, js), f"\npython: {json.dumps(py)[:2000]}\nnode:   {json.dumps(js)[:2000]}")
        self.assertEqual(drawn[len(SPECS):], [None] * len(bad))


if __name__ == "__main__":
    unittest.main()
