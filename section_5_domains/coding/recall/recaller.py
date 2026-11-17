from __future__ import annotations

from typing import Any, Dict, List


class CodingRecaller:
    """Recall Coding experience through the supplied Memory bridge."""

    def recall(self, *, task: str, memory_bridge) -> str:
        if memory_bridge is None:
            return ""

        try:
            successes: List[Dict[str, Any]] = (
                memory_bridge.recall_tested(
                    query=task,
                    domain="Cod",
                    limit=5,
                )
            )
            failures: List[Dict[str, Any]] = (
                memory_bridge.recall_rejections(
                    query=task,
                    domain="Cod",
                    limit=5,
                )
            )
            observations: List[Dict[str, Any]] = memory_bridge.recall(
                query=task,
                memory_class="derived",
                domain="Cod",
                limit=5,
            )

            lines = []

            if successes:
                lines.append("Previously successful solutions:")
                for item in successes:
                    lines.append(
                        f"  [{item['state']}] {item['title']} "
                        f"(score={item['score']:.2f}, "
                        f"success={item['success_count']}, "
                        f"fail={item['failure_count']})\n"
                        f"    Source memory: {item.get('id', 'unknown')}\n"
                        f"    Evidence: {str(item.get('content', ''))[:1500]}"
                    )

            if observations:
                lines.append(
                    "Previously observed Coding runs (not established as successful solutions):"
                )
                for item in observations:
                    lines.append(
                        f"  {item['title']} (state={item.get('state', 'derived')})\n"
                        f"    Source memory: {item.get('id', 'unknown')}\n"
                        f"    Evidence: {str(item.get('content', ''))[:1500]}"
                    )

            if failures:
                lines.append(
                    "Previously rejected approaches (reassess conditions before retrying):"
                )
                for item in failures:
                    lines.append(
                        f"  {item['title']} - "
                        f"{item.get('content', '')[:200]}"
                    )

            if lines:
                print(
                    "[coding] memory recall: "
                    f"{len(successes)} tested solutions, "
                    f"{len(observations)} derived observations, "
                    f"{len(failures)} failures"
                )

            return "\n".join(lines)

        except Exception as exc:
            print(f"[coding] memory recall failed: {exc}")
            return ""
