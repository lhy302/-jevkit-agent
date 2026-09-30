"""Portable tests for string/comment preservation during DSL translation."""
import ast
import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest


spec = importlib.util.spec_from_file_location("jevkit", Path(__file__).with_name("jevkit-agent.py"))
jev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(jev)


class DslLiteralTests(unittest.TestCase):
    def test_normalize_only_syntax_punctuation(self):
        self.assertEqual(jev.NormalizeDsl.normalize_text('输出（"你好，世界：（测试）"，真）'),
                         '输出("你好，世界：（测试）", 真)')

    def test_normalize_preserves_single_quotes(self):
        self.assertEqual(jev.NormalizeDsl.normalize_text("设 文本 = '真，假：空（且）'"),
                         "设 文本 = '真，假：空（且）'")

    def test_normalize_preserves_comments(self):
        text = '如果 真： # 说明：真，假（空）\n    输出（"真"）'
        self.assertEqual(jev.NormalizeDsl.normalize_text(text),
                         '如果 真: # 说明：真，假（空）\n    输出("真")')

    def test_normalize_preserves_multiline_literal_whitespace(self):
        text = '设 文本 = """真，第一行  \n    第二行：（空）  \n"""\n输出（文本）\n'
        self.assertEqual(jev.NormalizeDsl.normalize_text(text), text.replace('输出（文本）', '输出(文本)'))

    def test_spec_preserves_strings_and_converts_boolean(self):
        line = '输出("真", "假", "空", "且", "或", "非", 真, 假, 空)'
        result = jev.TemplateEngine.render_spec_line(line, '/python/io/output')
        self.assertTrue(result.startswith('输出("真", "假", "空", "且", "或", "非", True, False, None)'))
        self.assertIn('# node:/python/io/output', result)

    def test_code_output_preserves_string_meaning(self):
        code = jev.TemplateEngine.render_code_line('输出("真", "空", "且", 真)')
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exec(code, {})
        self.assertEqual(output.getvalue(), '真 空 且 True\n')

    def test_reverse_preserves_english_strings(self):
        self.assertEqual(jev.TemplateEngine.reverse_to_high('输出("True", "None", True, None)'),
                         '输出("True", "None", 真, 空)')

    def test_keywords_in_identifiers_are_not_replaced(self):
        self.assertEqual(jev.TemplateEngine.render_code_line('设 真值 = 假值'), '真值 = 假值')

    def test_escaped_double_quote_does_not_end_string(self):
        text = '真 " 假 \\ 空，：（）'
        source = '输出(' + repr(text) + ', 真)'
        code = jev.TemplateEngine.render_code_line(source)
        parsed = ast.parse(code).body[0].value
        self.assertEqual(ast.literal_eval(parsed.args[0]), text)
        self.assertTrue(ast.literal_eval(parsed.args[1]))

    def test_escaped_single_quote_does_not_end_string(self):
        source = "输出('真\\'假', 真)"
        self.assertEqual(jev.TemplateEngine.render_code_line(source), "print('真\\'假', True)")

    def test_even_backslashes_allow_quote_to_close(self):
        source = '输出("真\\\\", 真)'
        self.assertEqual(jev.TemplateEngine.render_code_line(source), 'print("真\\\\", True)')

    def test_raw_string_is_preserved(self):
        self.assertEqual(jev.TemplateEngine.render_code_line('输出(r"真\\空，：（）", 真)'),
                         'print(r"真\\空，：（）", True)')

    def test_simple_f_string_text_is_preserved(self):
        self.assertEqual(jev.TemplateEngine.render_code_line('输出(f"真，{value}", 真)'),
                         'print(f"真，{value}", True)')

    def test_node_text_in_string_is_not_removed(self):
        self.assertEqual(jev.TemplateEngine.render_code_line('设 text = "# node:/python/io/output"'),
                         'text = "# node:/python/io/output"')

    def test_real_node_annotation_is_removed(self):
        source = '输出("# node:/python/io/output", 真) # node:/python/io/output'
        self.assertEqual(jev.TemplateEngine.render_code_line(source),
                         'print("# node:/python/io/output", True)')

    def test_comment_keywords_are_preserved(self):
        self.assertEqual(jev.TemplateEngine.render_code_line('设 value = 真 # 真 假 空 且 或 非'),
                         'value = True # 真 假 空 且 或 非')

    def test_python_floor_division_does_not_start_comment(self):
        self.assertEqual(jev.TemplateEngine.render_code_line('设 value = 5 // 2 + 真'),
                         'value = 5 // 2 + True')

    def test_c_char_string_and_comment_are_preserved(self):
        source = '返回 check("真", \'假\', 真) // 真 假 空'
        mapped = jev._map_dsl_code(source, lambda code: jev._replace_dsl_literals(
            code, jev.TemplateEngine.LITERAL_MAP['c']), lang='c')
        self.assertEqual(mapped, '返回 check("真", \'假\', true) // 真 假 空')

    def test_block_comment_state_is_preserved(self):
        state = {}
        mapping = lambda code: jev._replace_dsl_literals(code, {'真': 'true'})
        first = jev._map_dsl_code('真 /* 真，', mapping, 'c', state)
        second = jev._map_dsl_code('真 */ 真', mapping, 'c', state)
        self.assertEqual((first, second), ('true /* 真，', '真 */ true'))

    def test_javascript_backtick_literal_is_preserved(self):
        source = '输出(`真，空（测试）`, 真)'
        self.assertEqual(jev.TemplateEngine.render_spec_line(source, None, 'javascript'),
                         '输出(`真，空（测试）`, true)')

    def test_multiline_spec_does_not_insert_nodes_into_string(self):
        state = {}
        lines = ['设 text = """真  ', '返回 真 # 真', '"""', '输出(真)']
        results = [jev.TemplateEngine.render_spec_line(line, '/python/data/assign', lex_state=state)
                   for line in lines]
        self.assertEqual(results[:3], lines[:3])
        self.assertIn('True', results[3])
        self.assertIn('node:', results[3])

    def test_comment_like_line_can_close_multiline_string(self):
        state = {}
        lines = ['设 text = """真', '# 空"""', '输出(真)']
        results = [jev.TemplateEngine.render_code_line(line, lex_state=state) for line in lines]
        self.assertEqual(results, ['text = """真', '# 空"""', 'print(True)'])

    def test_reverse_multiline_string_preserves_content(self):
        state = {}
        lines = ['设 text = """True  ', 'None，False  ', '"""', '输出(True)']
        results = [jev.TemplateEngine.reverse_to_high(line, lex_state=state) for line in lines]
        self.assertEqual(results[:3], lines[:3])
        self.assertEqual(results[3], '输出(真)')

    def test_end_to_end_full_and_incremental_translation(self):
        with tempfile.TemporaryDirectory() as td:
            high = Path(td) / 'demo.high.dsl'
            content = ('设 text = """真，第一行  \n    空：（第二行）  \n"""\n'
                       '输出(text)\n输出（"真，假：空（且）"，真）')
            high.write_text('# @jev-block:demo_001:begin\n' + content +
                            '\n# @jev-block:demo_001:end\n', encoding='utf-8')
            jev.jev_high_to_spec(str(high))
            jev.jev_spec_to_code(str(high))
            code_path = Path(td) / 'demo.py'
            code = code_path.read_text(encoding='utf-8')
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exec(compile(code, str(code_path), 'exec'), {})
            self.assertEqual(output.getvalue(), '真，第一行  \n    空：（第二行）  \n\n真，假：空（且） True\n')
            jev.jev_translate_block('demo_001', 'spec_to_code', str(high))
            self.assertEqual(code_path.read_text(encoding='utf-8').rstrip(), code.rstrip())
            jev.jev_spec_to_high(str(high))
            restored_high = high.read_text(encoding='utf-8')
            self.assertIn('"真，假：空（且）"', restored_high)
            self.assertIn('真，第一行  \n    空：（第二行）  \n', restored_high)


if __name__ == '__main__':
    unittest.main()
