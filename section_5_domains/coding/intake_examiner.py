"""Coding proposes independently checkable source-structure observations.

No source execution, model calls, memory writes, or host filesystem access.
Parsing does not establish program correctness or the truth of its comments.
"""
import ast
from collections import OrderedDict
import hashlib
import json
from pathlib import PurePosixPath
import re


class CodingIntakeExaminer:
    def __init__(self):
        self._attestations=OrderedDict()

    @staticmethod
    def key(proposal):
        fields={name:proposal.get(name) for name in ('domain','kind','title','content','source_refs','source')}
        return hashlib.sha256(json.dumps(fields,sort_keys=True,ensure_ascii=False).encode()).hexdigest()

    def examine(self, source, existing_knowledge=()):
        text=str(source['content']).split('\n\nTrainer-provided intake context (not independently verified):\n',1)[0]
        metadata=source.get('source') or {}
        filename=str(metadata.get('source_path') or source.get('title') or '')
        blocks=[]
        if metadata.get('source_kind')=='folder':
            for match in re.finditer(r'^----- (.+?) -----\n(.*?)(?=^----- .+? -----\n|\Z)',text,re.M|re.S):
                if match[1].endswith('.py'):
                    blocks.append((match[1],match[2]))
        elif filename.endswith('.py'):
            blocks=[(filename,text)]
        else:
            blocks=[(f'python-block-{i+1}.py',match[1]) for i,match in enumerate(re.finditer(r'```python\s*\n(.*?)```',text,re.S))]
        if len(blocks)>64:
            return {'status':'error','error':'Source contains more than 64 code blocks; split the intake'}
        analysis={'source_refs':list(source.get('source_refs') or []),
                  'provenance':'provided_unverified' if metadata.get('source_path') else 'not_supplied',
                  'origin_authenticity':'not_independently_verified',
                  'declared_source_hash_matches':hashlib.sha256(text.encode()).hexdigest()==metadata['sha256'] if metadata.get('sha256') else None,
                  'source_fingerprint':hashlib.sha256(source['content'].encode()).hexdigest(),
                  'verification':'untestable','scope':'Python syntax and structural facts only',
                  'blocks_identified':len(blocks),'blocks_examined':0,'failures':[],
                  'comparison_context_ids':[item['id'] for item in existing_knowledge],
                  'comparison_scope':'bounded domain context; final duplicate/conflict decisions belong to Mind'}
        candidates=[]
        fingerprints={hashlib.sha256(item.get('content','').strip().encode()).hexdigest():item['id'] for item in existing_knowledge}
        for filename,code in blocks:
            if len(code.encode())>1024*1024:
                raise ValueError('A code block exceeds 1 MiB; split the source before examination')
            analysis['blocks_examined']+=1
            try:
                tree=ast.parse(code,filename=filename)
                compile(tree,filename,'exec',dont_inherit=True)  # Compile, never execute.
            except (SyntaxError,ValueError,RecursionError) as exc:
                analysis['failures'].append({'block':filename,'reason':type(exc).__name__,'line':getattr(exc,'lineno',None)})
                continue
            digest=hashlib.sha256(code.encode()).hexdigest()
            functions=[{'name':node.name,'parameters':ast.unparse(node.args),'returns':ast.unparse(node.returns) if node.returns else None}
                       for node in tree.body if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef))]
            payload={'source_label':filename,'source_sha256':digest,'functions':functions,
                     'classes':[node.name for node in tree.body if isinstance(node,ast.ClassDef)]}
            document={'schema_version':1,'domain':'Cod','kind':'python_structure',
                      'verification_scope':'syntax and declared structure; behavior unverified','payload':payload}
            candidate={'domain':'Cod','kind':'observation','title':'Python structure: '+PurePosixPath(filename).name,
                       'content':json.dumps(document,sort_keys=True,ensure_ascii=False),
                       'source_refs':[source['id']],
                       'source':{'type':'domain','component':'coder','intake_examiner_version':1,
                                 'semantic_key':'python-source:'+filename,'raw_content_hash':analysis['source_fingerprint']},
                       'evidence':{'method':'ast.parse + compile without execution','source_sha256':digest,
                                   'functional_correctness_established':False}}
            candidate['evidence']['matching_context_id']=fingerprints.get(hashlib.sha256(candidate['content'].strip().encode()).hexdigest())
            self._attestations[self.key(candidate)]=candidate['evidence']
            while len(self._attestations)>256:
                self._attestations.popitem(last=False)
            candidates.append(candidate)
        analysis['verification']='failed' if analysis['failures'] else ('passed' if blocks else 'untestable')
        analysis['reason']=('Some blocks did not pass Python syntax verification' if analysis['failures'] else
                            'Syntax and structural observations checked; program behavior remains unverified' if blocks else
                            'No supported Python source blocks found; material remains Raw and requires domain-specific evaluation')
        return {'status':'ok','analysis':analysis,'candidates':candidates}

    def evaluate(self, proposal):
        evidence=self._attestations.get(self.key(proposal))
        return {'ok':evidence is not None,'testable':evidence is not None,
                'reason':'Matches an examined syntax/structure observation; not a behavioral correctness claim' if evidence else 'No matching intake examination attestation',
                'evidence':dict(evidence or {})}
