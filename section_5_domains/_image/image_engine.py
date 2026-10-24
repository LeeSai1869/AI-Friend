from mind.organ import Organ

class ImageOrgan(Organ):
    name = "image"
    kind = "domain"
    scope = "outside_guards"
    capabilities = ["compose", "render", "identify_concepts"]
    keywords = ["draw", "image", "picture", "render", "sketch", "paint"]

    def can_handle(self, request):
        text = (request.get("text") or "").lower()
        return any(k in text for k in self.keywords)

    def handle(self, request):
        return {"status": "ok", "output": f"[image] Received: {request.get('text')}"}

ORGAN = ImageOrgan()