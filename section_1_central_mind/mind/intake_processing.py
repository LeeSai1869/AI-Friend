"""Generic Mind-owned post-intake examination and knowledge decisions."""
from __future__ import annotations
import hashlib
from .resource_socket import ResourceRequirement


class RawIntakeProcessor:
    def __init__(self, mind):
        self.mind = mind

    def run(self, raw_id, *, retry=False):
        mind = self.mind
        service = mind.memory_service
        if service is None:
            raise RuntimeError('Memory Service is unavailable')
        queued = service.enqueue_raw(raw_id)
        token = service.processing.claim(raw_id, retry=retry)
        if token is None:
            return service.processing.status(raw_id)
        def finish(state, **payload):
            return service.processing.finish(raw_id, token, state=state, payload=payload)
        knowledge_ids=[]
        decisions=[]
        try:
            source = mind.memory.get(raw_id)
            if source is None or source.get('memory_class') != 'raw':
                raise ValueError('Raw source is unavailable')
            if hashlib.sha256(source['content'].encode()).hexdigest() != queued['content_hash']:
                raise ValueError('Raw contents differ from the queued source fingerprint')
            raw_comparison = service.compare_raw_source(source)
            candidates = [info for info in mind.inventory.all() if info.kind == 'domain'
                          and (info.manifest or {}).get('memory_domain') == source['domain_created']]
            if len(candidates) != 1:
                return finish('deferred',processing='deferred',verification='untestable',decision='deferred',
                              reason='No unique domain owner is registered', knowledge_ids=[], raw_comparison=raw_comparison)
            info = candidates[0]
            declaration = (info.manifest or {}).get('intake_processing') or {}
            if declaration.get('mode') == 'deferred' or not declaration.get('capability'):
                return finish('deferred',processing='deferred',verification='not_attempted',decision='deferred',
                              domain_component=info.name, reason=declaration.get('reason') or 'Domain has no intake examiner',knowledge_ids=[], raw_comparison=raw_comparison)
            response = mind.resource_socket.request(
                ResourceRequirement(kind='domain',domain=info.name,capability=declaration['capability']),
                request={'mode':'intake_processing','raw_source':source,
                         'existing_knowledge':service.examination_context(source['domain_created'])}, cognitive_plan={})
            if not isinstance(response,dict) or response.get('status') != 'ok':
                raise RuntimeError((response or {}).get('error') or 'Domain examination failed')
            analysis = response.get('analysis') or {}
            analysis['raw_comparison'] = raw_comparison
            proposed = response.get('candidates') or []
            if not isinstance(proposed,list) or len(proposed)>64:
                raise ValueError('Invalid domain candidate batch')
            decisions=[]
            knowledge_ids=[]
            for candidate in proposed:
                if not isinstance(candidate,dict) or candidate.get('domain') != source['domain_created']:
                    raise ValueError('Domain proposed a candidate for another domain')
                if raw_id not in (candidate.get('source_refs') or []):
                    raise ValueError('Domain candidate omitted its Raw provenance')
                comparison = service.reconcile_candidate(candidate)
                if comparison['status'] != 'new':
                    decision='duplicate' if comparison['status']=='duplicate' else 'deferred'
                    decisions.append({'decision':decision,'comparison':comparison})
                    if decision=='duplicate':
                        knowledge_ids.extend(comparison['memory_ids'])
                    continue
                # A domain can only submit a proposal. Mind owns every commit.
                proposal = mind.memory.propose_knowledge(
                    title=candidate['title'],content=candidate['content'],domain=candidate['domain'],
                    kind=candidate.get('kind','observation'),requested_class='tested',
                    source_refs=candidate['source_refs'],source=candidate.get('source') or {},
                    evidence=candidate.get('evidence') or {},
                    derivation_note='Domain examination of preserved Raw material; verification scope is recorded.')
                evaluation=(proposal.get('learning_evaluation') or {})
                if evaluation.get('testable') is True and evaluation.get('ok') is True:
                    committed=mind.decide_memory_proposal(proposal['proposal_id'],approved=True,memory_class='tested',
                        reason=evaluation.get('reason') or 'Domain checks passed for this candidate')
                    knowledge_ids.append(committed['memory_id'])
                    decisions.append({'decision':'duplicate' if committed.get('reused_existing') else 'accepted','proposal_id':proposal['proposal_id'],'memory_id':committed['memory_id']})
                elif evaluation.get('testable') is True:
                    mind.decide_memory_proposal(proposal['proposal_id'],approved=False,reason=evaluation.get('reason') or 'Domain verification failed')
                    decisions.append({'decision':'rejected','proposal_id':proposal['proposal_id']})
                else:
                    decisions.append({'decision':'deferred','proposal_id':proposal['proposal_id']})
            labels={item['decision'] for item in decisions}
            decision=('accepted' if labels=={'accepted'} else 'duplicate' if labels=={'duplicate'} else
                      'mixed' if len(labels)>1 else next(iter(labels),'duplicate' if raw_comparison['status']=='duplicate' else 'deferred'))
            if analysis.get('failures') and knowledge_ids:
                decision='partial'
            return finish('completed',processing='completed',verification=analysis.get('verification','untestable'),
                          decision=decision,domain_component=info.name,analysis=analysis,decisions=decisions,
                          reason=analysis.get('reason',''),knowledge_ids=list(dict.fromkeys(knowledge_ids)))
        except Exception as exc:
            return finish('processing_failed',processing='failed',verification='not_attempted',decision='pending',
                          reason=str(exc),knowledge_ids=list(dict.fromkeys(knowledge_ids)),decisions=decisions)
