from unittest import TestCase

from click.testing import CliRunner
from lxml import etree
from mock import patch

from regparser.commands.parse_rule_changes import parse_rule_changes
from regparser.index import dependency, entry
from regparser.notice.xml import NoticeXML
from regparser.test_utils.xml_builder import XMLBuilder


class CommandsParseRuleChangesTests(TestCase):
    def setUp(self):
        super(CommandsParseRuleChangesTests, self).setUp()
        self.cli = CliRunner()
        with XMLBuilder("ROOT") as ctx:
            ctx.PRTPAGE(P="1234")
        self.notice_xml = NoticeXML(ctx.xml)

    def test_missing_notice(self):
        """If the necessary notice XML is not present, we should expect a
        dependency error"""
        with self.cli.isolated_filesystem():
            result = self.cli.invoke(parse_rule_changes, ['1111'])
            self.assertTrue(isinstance(result.exception,
                                       dependency.Missing))

    @patch('regparser.commands.parse_rule_changes.fetch_amendments')
    def test_writes(self, fetch_amendments):
        """If the notice XML is present, we write the parsed version to disk,
        even if that version's already present"""
        fetch_amendments.return_value = ['something']
        with self.cli.isolated_filesystem():
            entry.Notice('1111').write(self.notice_xml)
            self.cli.invoke(parse_rule_changes, ['1111'])
            self.assertTrue(fetch_amendments.called)
            args = fetch_amendments.call_args[0]
            self.assertTrue(isinstance(args[0], etree._Element))

            fetch_amendments.reset_mock()
            entry.Entry('rule_changes', '1111').write('content')
            self.cli.invoke(parse_rule_changes, ['1111'])
            self.assertTrue(fetch_amendments.called)
