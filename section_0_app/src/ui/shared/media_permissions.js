import { onAuthenticated, onMessage, sendRaw, isAuthenticated, onAuthStateChange } from './auth_session/session.js';

const panel = document.createElement('aside');
panel.setAttribute('aria-label', 'Media permissions');
panel.style.cssText = 'position:fixed;bottom:80px;right:20px;max-width:420px;max-height:55vh;overflow:auto;background:var(--bg-panel,#20232b);color:var(--text,#fff);padding:16px;border:1px solid #888;z-index:10000;display:none';
const requests = document.createElement('div');
const outcome = document.createElement('pre');
outcome.style.cssText = 'white-space:pre-wrap;max-height:180px;overflow:auto';
const close = document.createElement('button');
close.textContent = 'Dismiss results';
close.onclick = () => { outcome.textContent = ''; panel.style.display = requests.childElementCount ? 'block' : 'none'; };
panel.append(requests, outcome, close);
document.body.append(panel);

let permissionListPending = false;
function refresh() {
  // A long model turn serializes this session's backend operations. Never
  // accumulate polling requests while its first response is still outstanding.
  if (isAuthenticated() && !permissionListPending) {
    permissionListPending = true;
    sendRaw({ op:'permission_list' });
  }
}
onAuthenticated(refresh);
onAuthStateChange(() => { if (!isAuthenticated()) { permissionListPending = false; requests.replaceChildren(); outcome.textContent = ""; panel.style.display = "none"; } });
setInterval(refresh, 5000);
onMessage(message => {
  if (!isAuthenticated()) { panel.style.display = 'none'; return; }
  if (message.op === 'permission_requests') {
    permissionListPending = false;
    requests.replaceChildren();
    for (const request of message.requests || []) {
      const card = document.createElement('div');
      const text = document.createElement('p');
      text.textContent = request.description;
      card.append(text);
      for (const [label, approved] of [['Allow once', true], ['Deny', false]]) {
        const button = document.createElement('button');
        button.textContent = label;
        button.onclick = () => {
          for (const child of card.querySelectorAll('button')) child.disabled = true;
          sendRaw({ op:'permission_decide', request_id:request.request_id, approved });
          card.remove();
          outcome.textContent = approved ? 'Running approved media analysis…' : 'Media analysis denied.';
        };
        card.append(button);
      }
      requests.append(card);
    }
    panel.style.display = requests.childElementCount || outcome.textContent ? 'block' : 'none';
  }
  if (message.op === 'permission_result') {
    outcome.textContent = message.error || (message.state === 'denied' ? 'Media analysis denied.' : JSON.stringify(message.result, null, 2));
    panel.style.display = 'block';
    refresh();
  }
});
