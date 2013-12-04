#vim: set encoding=utf-8
from unittest import TestCase
from lxml import etree
from lxml import html

from regparser.tree.node_stack import NodeStack
from regparser.tree.xml_parser import appendices, tree_utils


class AppendicesTest(TestCase):
    def test_process_appendix_supplement(self):
        xml = u"""
        <APPENDIX>
            <EAR>Pt. 1111, Supp. I</EAR>
            <HD SOURCE="HED">
                Supplement I to Part 1111—Official Interpretations</HD>
            <P>Content</P>
        </APPENDIX>
        """
        self.assertEqual(appendices.process_appendix(etree.fromstring(xml),
                                                     1111), None)

    def test_process_appendix(self):
        """Integration test for appendices"""
        xml = u"""
        <APPENDIX>
            <EAR>Pt. 1111, App. A</EAR>
            <HD SOURCE="HED">Appendix A to Part 1111—Awesome</HD>
            <P>Intro text</P>
            <HD SOURCE="HD1">Header 1</HD>
            <P>Content H1-1</P>
            <P>Content H1-2</P>
            <HD SOURCE="HD2">Subheader</HD>
            <P>Subheader content</P>
            <HD SOURCE="HD1">Header <E T="03">2</E></HD>
            <P>Final <E T="03">Content</E></P>
            <GPH>
                <PRTPAGE P="650" />
                <GID>MYGID</GID>
            </GPH>
        </APPENDIX>
        """
        appendix = appendices.process_appendix(etree.fromstring(xml), 1111)
        self.assertEqual(3, len(appendix.children))
        intro, h1, h2 = appendix.children

        self.assertEqual([], intro.children)
        self.assertEqual("Intro text", intro.text.strip())

        self.assertEqual(3, len(h1.children))
        self.assertEqual('Header 1', h1.title)
        c1, c2, sub = h1.children
        self.assertEqual([], c1.children)
        self.assertEqual('Content H1-1', c1.text.strip())
        self.assertEqual([], c2.children)
        self.assertEqual('Content H1-2', c2.text.strip())

        self.assertEqual(1, len(sub.children))
        self.assertEqual('Subheader', sub.title)
        self.assertEqual('Subheader content', sub.children[0].text.strip())

        self.assertEqual(2, len(h2.children))
        self.assertEqual('Header 2', h2.title)
        self.assertEqual('Final Content', h2.children[0].text.strip())
        self.assertEqual('![](MYGID)', h2.children[1].text.strip())
