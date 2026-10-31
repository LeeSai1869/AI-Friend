# Administrator URL exclusions — build 2026.10.31.3

Local command-line controls, not model tools:

```sh
python3 scripts/url_policy.py block bank.example
python3 scripts/url_policy.py block https://other.example/private
python3 scripts/url_policy.py list
python3 scripts/url_policy.py unblock bank.example
```

Use your actual bank's domain, not account numbers, passwords or secret links.
A host rule blocks that host and subdomains, both HTTP schemes, and all ports.
A URL path rule additionally restricts matching to that path and descendants;
queries/fragments are ignored. Whole-site exclusions are recommended because a
website can expose the same financial information at many different endpoints.
Distinct service domains need separate rules. Lookalike domains do not match.

The persistent policy is shared by development and installed builds at:
`~/Library/Application Support/AI Friend V1/network_policy.json`.
An explicit AI_FRIEND_URL_POLICY environment setting overrides that location;
normal Mac launches do not set it. New calls read current rules; restart browsers
when changing rules during an active interaction. This patch has a CLI control,
not a settings-screen toggle. Rules have no effect in older app versions.

Enforcement: web_fetch checks direct destinations and every redirect before
contact. browser_interact checks requests before allowing navigation or
subresources, independently of the caller's allowed_origins. Browser sockets
remain blocked. Search checks its configured mainstream service destinations and
filters excluded result URLs. An existing malformed/unreadable policy fails
closed. A missing policy means no user exclusions have yet been configured.

The CLI is administrator-operated by convention, not a password-authenticated
settings service; protect the policy using account/filesystem administration if
other local users are untrusted. This does not protect arbitrary programs,
provider traffic or coding subprocesses at OS level. It is not a firewall, nor
protection against a malicious local administrator. No existing memory is erased,
and existing source/login data is not removed. Browsers still use fresh isolated
profiles without the user's logged-in banking sessions. Domain rules cannot
identify banking services generically or prevent pasted sensitive information
from being sent to a permitted endpoint; that requires separate data controls.

Validation: 565 tests and 15 subtests passed; 3 optional integration tests skipped.
A separate focused run passed 19 tests with real Chromium enabled, including
blocking a same-origin denied subrequest while allowing the rest of the page.
Redirect tests verify the blocked destination receives no fetch call.
