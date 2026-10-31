from pathlib import Path
import shutil
import subprocess
import pytest


def test_slow_turn_cannot_accumulate_permission_poll_requests():
    node=shutil.which('node')
    if not node:pytest.skip('Node is needed to execute the UI module regression')
    root=Path(__file__).resolve().parents[1]
    source=(root/'section_0_app/src/ui/shared/media_permissions.js').read_text().split('\n',1)[1]
    harness='''
const assert=require('assert');
const hooks={}; const sent=[]; let authenticated=true;
const onAuthenticated=fn=>hooks.auth=fn;
const onAuthStateChange=fn=>hooks.state=fn;
const onMessage=fn=>hooks.message=fn;
const isAuthenticated=()=>authenticated;
const sendRaw=message=>sent.push(message);
const setInterval=fn=>hooks.tick=fn;
class Element {
  constructor(){this.style={};this.children=[];this.textContent='';}
  setAttribute(){} append(...items){this.children.push(...items);}
  replaceChildren(){this.children=[];}
  get childElementCount(){return this.children.length;}
}
const document={createElement:()=>new Element(),body:new Element()};
'''+source+'''
hooks.auth();
for(let i=0;i<100;i++)hooks.tick();
assert.strictEqual(sent.length,1,'awaiting reply must suppress all further polls');
hooks.message({op:'permission_requests',requests:[]});
hooks.tick(); assert.strictEqual(sent.length,2);
authenticated=false;hooks.state({authenticated:false});hooks.tick();
assert.strictEqual(sent.length,2);
authenticated=true;hooks.auth();assert.strictEqual(sent.length,3);
'''
    result=subprocess.run([node,'-e',harness],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
