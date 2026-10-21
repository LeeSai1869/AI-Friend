# Coding execution

Coding has separate inspection, planning, testing, verification, and change flows. Trusted read-only requests cannot be converted into writes by a model. Its bounded loop recalls Memory Service evidence, inspects files through Broker, requests capability-selected model assistance, validates candidates, runs existing tests in a disposable snapshot, repairs failures, applies passing candidates through guarded writes, compiles syntax, and retests the persisted project. Unclear tasks and unavailable resources return questions to Mind and Chat.

Candidate validation has a three-attempt budget; functional repair has a two-repair budget. Existing discovered tests cannot be omitted by a model returning an empty list. No tests means no claim of functional verification. Multi-file application is not transactional: a denied/failed later write stops the run and reports prior writes that remain.

Python compilation uses in-process syntax compilation without executing source or importing workspace modules. Functional tests run only under the existing Trainer-only `code.test.execute` capability. General `process.execute` remains denied. Coding does not invoke raw subprocesses or write source outside Broker.

## Isolated functional tests

The unittest/pytest runner uses an explicitly selected locally installed immutable Docker image. It stages a bounded UTF-8 snapshot into a disposable container with Docker copy, then starts, waits, reads bounded logs, and removes its own container. There are no host mounts, Docker sockets, home directories, credentials, or network access. It runs as UID/GID 65534 with capabilities dropped, privilege escalation disabled, and CPU/memory/process/time limits. Its disposable writable container filesystem is not the host project.

Limits: 200 files, 4 MiB source/fixtures, 50 test modules, at most 60 seconds. Project dependencies must already exist in the reviewed image; tests cannot install packages or select another image. Pytest plugin autoload is disabled. Empty, entirely skipped, and entirely expected-failure suites do not pass. Test evidence covers only the behaviors executed. Other languages require constrained adapters.

Build with a reviewed immutable Python base (pull it first if needed):

```sh
.venv/bin/python scripts/build_test_image.py --base python@sha256:YOUR_REVIEWED_DIGEST
export AI_FRIEND_TEST_IMAGE=$(docker image inspect ai-friend-coding-tests --format '{{.Id}}')
AI_FRIEND_RUN_CONTAINER_TESTS=1 .venv/bin/python -m pytest tests/test_python_test_profile.py -q
```

The builder downloads pinned wheels on the host over verified TLS, derives their SHA256 lock, and builds offline. Only wheels, their lock, and the Dockerfile enter the build context. It was exercised successfully in this cloud environment, followed by actual container tests and the browser repair cycle. Set a writable `DOCKER_CONFIG` if the Docker builder cannot write its default configuration directory.

Launch the desktop from a shell exporting this image ID. In Coding, open a disposable Python project with behavioral tests and use **Run Python tests**, or request a change from Chat. Both windows use the same validated session and Mind; successful writes notify the open editor to refresh. No permanent memory writes occur directly in Coding: tested observations are evaluated and committed by Mind through Memory Service.

These checks establish the integrated execution path using deterministic model fixtures. Real-model task quality and native macOS window lifecycle remain separate runtime checks.
