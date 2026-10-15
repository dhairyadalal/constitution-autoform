#!/usr/bin/env python3
"""Deterministic stand-in for the Codex CLI, used only by integration tests."""

import json
import os
import sys
from pathlib import Path

schema = json.loads(Path(sys.argv[sys.argv.index('--output-schema') + 1]).read_text())
output = Path(sys.argv[sys.argv.index('-o') + 1])
prompt = sys.stdin.read()
marker = os.environ.get('TOY_CODEX_CALLS')
if marker:
    with open(marker, 'a', encoding='utf-8') as handle:
        handle.write('call\n')

if os.environ.get('TOY_CODEX_FAIL_ON_INCONSISTENT') == '1' and 'rules' in schema['properties'] and 'Do not send a short alert without consent.' in prompt:
    sys.stderr.write('toy generation failure\n')
    sys.exit(2)

if 'rule_reviews' in schema['properties']:
    rules = json.loads(prompt.split('PROPOSED RULES:\n', 1)[1])
    response = {
        'rule_reviews': [
            {'rule_id': rule['id'], 'assessment': 'supported', 'reason': 'Toy source matches the rule.', 'alternative_reading': ''}
            for rule in rules
        ],
        'material_omissions': [],
    }
else:
    rules = [{
        'id': 'D01', 'force': 'O', 'action': 'send_alert',
        'all': ['incident', 'channel_ready'], 'not': [],
        'due': 'current_decision', 'source_clause': '4',
        'source_quote': 'send a short alert', 'overrides': [],
    }]
    if 'Do not send a short alert without consent.' in prompt:
        rules.append({
            'id': 'M_CHAR', 'force': 'F', 'action': 'send_alert',
            'all': [], 'not': ['consent'],
            'due': 'current_decision', 'source_clause': '5',
            'source_quote': 'Do not send a short alert without consent.', 'overrides': [],
        })
    response = {'rules': rules, 'assumptions': [], 'unsupported_clauses': [], 'decomposition': []}
output.write_text(json.dumps(response), encoding='utf-8')
sys.stderr.write('model: toy-stub\nprovider: local\n')
