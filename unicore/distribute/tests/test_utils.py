import textwrap

from StringIO import StringIO
from unittest import TestCase

from unicore.distribute.utils import UCConfigParser


class TestUCConfigParser(TestCase):

    def setUp(self):
        sio = StringIO(textwrap.dedent("""
            [foo]
            list =
                1
                2
                3

            dict =
                a = 1
                b = 2
                c = 3
            """))
        self.cp = UCConfigParser()
        self.cp.readfp(sio)

    def test_get_list(self):
        self.assertEqual(self.cp.get_list('foo', 'list'), ['1', '2', '3'])

    def test_get_dict(self):
        self.assertEqual(self.cp.get_dict('foo', 'dict'), {
            'a': '1',
            'b': '2',
            'c': '3',
        })
