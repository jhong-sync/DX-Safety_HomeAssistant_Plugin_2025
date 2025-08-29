class TTSDispatcher:
    def __init__(self, cfg, publisher):
        self.cfg = cfg
        self.publisher = publisher
    async def maybe_say(self, cae: dict, decision):
        if not self.cfg.enabled:
            return
        text = self.cfg.template.format(**{
            "headline": cae.get("headline", ""),
            "description": cae.get("description", ""),
            "severity": cae.get("severity", "")
        })
        await self.publisher.publish_tts(self.cfg.topic, text, cae.get("severity", ""))
