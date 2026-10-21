"""Check registered resource availability and optionally real semantic generation.

Run with .venv/bin/python scripts/check_models.py --semantic.
No model names are hardcoded and no tools, project writes or memory writes run.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'section_1_central_mind'))
import bootstrap  # noqa: E402,F401
from section_7_models.model_router import ModelRouter  # noqa: E402
from section_7_models.interface import execution_model_for, provider_name_for  # noqa: E402
from mind.caller import Caller  # noqa: E402
from mind.inventory import Inventory  # noqa: E402
from mind.reasoner.understanding import SemanticUnderstanding  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--semantic', action='store_true', help='request a real semantic proposal using the production prompt')
    args = parser.parse_args()
    router = ModelRouter(ROOT / 'section_7_models/models_registry.yaml')
    requirement = {'domain': 'general', 'capability': 'reason', 'structured_output': 'json',
                   'traits': ['reasoning', 'instruction_following', 'reliable_json_output'],
                   'avoid_traits': ['reasoning_leak', 'overthinks', 'slow'], 'prefer_local': True}
    cache = {}
    print('Registered semantic candidates (in selection order):')
    for candidate in router._candidates(requirement):
        resource = candidate.resource
        try:
            available = router._available(resource, cache)
            status = 'available' if available else 'not installed at configured endpoint'
            if provider_name_for(resource) != 'ollama':
                status = 'registered; availability requires an inference request'
        except RuntimeError as exc:
            status = str(exc)
        print(f'  {candidate.key}: {execution_model_for(resource)} — {status}')
    if not args.semantic:
        print('Use --semantic to test the actual semantic prompt. This can take several minutes.')
        return 0
    caller = Caller(None, None, on_status=lambda message: print(message, flush=True))
    calls = []

    def semantic_resource(*, system, messages):
        result = router.fulfill(requirement=requirement, call_fn=caller._invoke_resource,
                                messages=[{'role': 'system', 'content': system}, *messages])
        calls.append({key: value for key, value in result.items() if key != 'output'})
        if not result.get('ok'):
            raise RuntimeError(json.dumps(result['attempts']))
        return result['output']

    understanding = SemanticUnderstanding(inventory=Inventory(ROOT).discover(), semantic_resource=semantic_resource)
    proposal = understanding.propose(objective='Can you read my project files?', supplied_context={},
                                     recalled_memory=[], evidence=[])
    print(json.dumps({'routing': calls, 'semantic_proposal': proposal}, indent=2))
    return 1 if proposal.get('error') else 0


if __name__ == '__main__':
    raise SystemExit(main())
