import logging, json, sys

class JsonFormatter(logging.Formatter):
    def format(self, record):
        base = {
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        if record.args:
            base.update(record.args)
        if hasattr(record, "extra"):
            base.update(getattr(record, "extra"))
        return json.dumps(base, ensure_ascii=False)

def get_logger():
    log = logging.getLogger("dxsafety")
    if not log.handlers:
        h = logging.StreamHandler(sys.stdout)
        h.setFormatter(JsonFormatter())
        log.addHandler(h)
        log.setLevel(logging.INFO)
    return log