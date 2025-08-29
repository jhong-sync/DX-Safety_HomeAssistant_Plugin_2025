from aiohttp import web

async def start_health_server(port: int, metrics, on_trigger_test=None):
    app = web.Application()

    async def index(_):
        return web.Response(text="DX-Safety is running. See /health and /metrics.", content_type="text/plain")

    async def health(_):
        return web.json_response({"status": "ok"})

    async def metrics_handler(_):
        return web.Response(text=metrics.render_prometheus(), content_type="text/plain")

    async def trigger_test(_):
        if on_trigger_test is None:
            return web.json_response({"ok": False, "error": "not_enabled"}, status=404)
        ok = await on_trigger_test()
        return web.json_response({"ok": bool(ok)})

    app.add_routes([
        web.get("/", index),
        web.get("/health", health),
        web.get("/metrics", metrics_handler),
        web.post("/trigger_test", trigger_test),
    ])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
