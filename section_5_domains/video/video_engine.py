from mind.organ import Organ

class VideoOrgan(Organ):
    name = "video"
    kind = "domain"
    scope = "outside_guards"
    capabilities = ["compose", "render", "identify_concepts"]
    keywords = ["video", "animation", "film", "clip", "footage", "storyboard"]

    def can_handle(self, request):
        text = (request.get("text") or "").lower()
        return any(k in text for k in self.keywords)

    def handle(self, request):
        return {"status": "ok", "output": f"[video] Received: {request.get('text')}"}

ORGAN = VideoOrgan()