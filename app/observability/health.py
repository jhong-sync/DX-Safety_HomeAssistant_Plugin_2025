from aiohttp import web

async def start_health_server(port: int, metrics):
    app = web.Application()

    async def health(_):
        return web.json_response({"status": "ok"})

    async def metrics_handler(_):
        return web.Response(text=metrics.render_prometheus(), content_type="text/plain")

    app.add_routes([web.get("/health", health), web.get("/metrics", metrics_handler)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()