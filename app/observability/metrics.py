class Counter:
    def __init__(self):
        self.val = 0
    def inc(self, n=1):
        self.val += n

class Metrics:
    def __init__(self, enabled=True):
        self.enabled = enabled
        self.alerts_received_total = Counter()
        self.alerts_valid_total = Counter()
        self.alerts_triggered_total = Counter()
        self.ingestor_reconnects_total = Counter()
    def render_prometheus(self):
        if not self.enabled:
            return ""
        lines = [
            f"alerts_received_total {self.alerts_received_total.val}",
            f"alerts_valid_total {self.alerts_valid_total.val}",
            f"alerts_triggered_total {self.alerts_triggered_total.val}",
            f"ingestor_reconnects_total {self.ingestor_reconnects_total.val}",
        ]
        return "\n".join(lines) + "\n"