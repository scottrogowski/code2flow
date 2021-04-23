import sys
import os
import pytest

sys.path.append(os.getcwd().split('/tests')[0])

# import lib.languages.python as python_implementation
# import lib.engine as engine

# lang = python_implementation.Lang


# def test_source_code():
#     sc = engine.SourceCode(open('tests/source_a').read(), lang=lang)
#     print(sc)
#     print("10:30")
#     print(sc[10:30])
#     print(":10")
#     print(sc[:10])
#     print("30:")
#     print(sc[30:])

#     print("now for a trick")
#     print(sc - sc[10:30])

#     assert False

# def test_remove_comments():
#     raw_source = open('tests/source_a').read()
#     source = engine.SourceCode(raw_source, lang=lang)
#     print(source)
#     assert False
