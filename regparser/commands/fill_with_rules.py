from collections import defaultdict
import copy
import logging

import click

from regparser import content
from regparser.index import dependency, entry
from regparser.notice.compiler import compile_regulation

logger = logging.getLogger(__name__)


def dependencies(tree_path, version_ids, cfr_title, cfr_part):
    """Set up the dependency graph for this regulation. First calculates
    "gaps" -- versions for which there is no existing tree. In this
    calculation, we ignore the first version, as we won't be able to build
    anything for it. Add dependencies for any gaps, tying the output tree to
    the preceding tree, the version info and the parsed rule"""
    existing_ids = set(tree_path)
    gaps = [(prev, curr) for prev, curr in zip(version_ids, version_ids[1:])
            if curr not in existing_ids]

    deps = dependency.Graph()
    for prev, curr in gaps:
        deps.add(tree_path / curr, tree_path / prev)
        deps.add(tree_path / curr, entry.RuleChanges(curr))
        deps.add(tree_path / curr,
                 entry.Version(cfr_title, cfr_part, curr))
    return deps


def derived_from_rules(version_ids, deps, tree_path):
    """We only want to process trees which are created by parsing rules. To do
    that, we'll filter by those trees which have a dependency on a parsed
    rule"""
    rule_versions = []
    for version_id in version_ids:
        path = str(tree_path / version_id)
        rule_change = str(entry.RuleChanges(version_id))
        if rule_change in deps.dependencies(path):
            rule_versions.append(version_id)
    return rule_versions


def process(tree_path, previous, version_id):
    """Build and write a tree by combining the preceding tree with changes
    present in the associated rule"""
    prev_tree = (tree_path / previous).read()
    notice = entry.RuleChanges(version_id).read()
    notice_changes = defaultdict(list)
    for amendment in notice.get('amendments', []):
        for label, change_list in amendment.get('changes', []):
            notice_changes[label].extend(change_list)
    changes = apply_patches(version_id, notice_changes)
    new_tree = compile_regulation(prev_tree, changes)
    (tree_path / version_id).write(new_tree)


def apply_patches(document_number, changes):
    """Changes can be present in the notice or in an external set inside the
    `content` module. If any are present in the latter, they extend the
    former"""
    # Don't want to modify the original; it may still be referenced
    changes = copy.deepcopy(changes)
    patches = content.RegPatches().get(document_number) or {}
    for key, value in patches.items():
        existing = changes.get(key, [])
        changes[key] = existing + value
    return changes


@click.command()
@click.argument('cfr_title', type=int)
@click.argument('cfr_part', type=int)
def fill_with_rules(cfr_title, cfr_part):
    """Fill in missing trees using data from rules. When a regulation tree
    cannot be derived through annual editions, it must be built by parsing the
    changes in final rules. This command builds those missing trees"""
    logger.info("Fill with rules - %s CFR %s", cfr_title, cfr_part)
    tree_path = entry.Tree(cfr_title, cfr_part)
    version_ids = list(entry.Version(cfr_title, cfr_part))
    deps = dependencies(tree_path, version_ids, cfr_title, cfr_part)

    preceeded_by = dict(zip(version_ids[1:], version_ids))
    derived = derived_from_rules(version_ids, deps, tree_path)
    for version_id in derived:
        deps.validate_for(tree_path / version_id)
        if deps.is_stale(tree_path / version_id):
            process(tree_path, preceeded_by[version_id], version_id)
