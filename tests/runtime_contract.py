"""Current generic socket contract for tests whose subject is execution, not semantics."""
from types import SimpleNamespace

from section_1_central_mind.mind.cognition import CognitivePlan, CognitiveStep
from section_1_central_mind.mind.resource_socket import ResourceSocket


def configure_execution_contract(mind, infos):
    for info in infos:
        info.capabilities = ['perform']
    mind.inventory = SimpleNamespace(all=lambda: infos, get=lambda name: next((item for item in infos if item.name == name), None))
    mind._domain_brokers = {}
    if not hasattr(mind, 'memory_service'):
        mind.memory_service = None
    mind.resource_socket = ResourceSocket()
    mind.resource_socket.connect('domain', mind._fulfill_domain_requirement)
    mind.reasoner = SimpleNamespace(plan=lambda objective, **kwargs: CognitivePlan(
        objective=objective,
        steps=[CognitiveStep(step_id=f'step-{i}', objective=objective, kind='domain',
                             component=info.name, capability='perform') for i, info in enumerate(infos)],
    ))
