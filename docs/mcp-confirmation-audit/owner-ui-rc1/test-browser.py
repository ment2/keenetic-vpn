"""Synthetic local Chromium UI test. No production service or ChatGPT calls."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from functools import partial
from pathlib import Path
from threading import Thread
from playwright.sync_api import sync_playwright, expect
import os, shutil, tempfile

ROOT = Path(__file__).resolve().parent
ASSETS = ['demo.html','demo.css','demo.mjs','owner-review.mjs']
class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *_): pass
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        super().end_headers()

with tempfile.TemporaryDirectory() as d:
    for name in ASSETS: shutil.copyfile(ROOT/name,Path(d)/name)
    server = ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=d))
    thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f'http://127.0.0.1:{server.server_port}/'
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path=os.environ.get('CHROMIUM_BIN') or shutil.which('chromium'),headless=True,args=['--disable-background-networking','--disable-sync','--no-default-browser-check'])
            context=browser.new_context(viewport={'width':960,'height':900},service_workers='block')
            outbound=[]; errors=[]
            def route(r):
                if r.request.url.startswith(base): r.continue_()
                else: outbound.append(r.request.url);r.abort()
            context.route('**/*',route)
            page=context.new_page();page.on('pageerror',lambda e: errors.append(str(e)))
            def start():
                page.goto(base+'demo.html');expect(page.locator('#status')).to_have_text('REVIEW')
            def approve():
                page.locator('#agree').check();page.locator('#approve').click();expect(page.locator('#status')).to_have_text('APPROVED')
            def count(a,b):
                expect(page.locator('#counter')).to_have_text(f'Запросы согласования: {a} · тестовые постановки: {b}')
            start();expect(page.locator('#approve')).to_be_disabled();expect(page.locator('#allow')).to_be_disabled();count(0,0)
            print('PASS 1: initial load has no approval or enqueue')
            page.locator('#agree').check();page.locator('#approve').evaluate('(el)=>el.click()');expect(page.locator('#status')).to_have_text('REVIEW');count(0,0)
            print('PASS 2: synthetic programmatic click cannot approve')
            page.locator('#approve').click();expect(page.locator('#status')).to_have_text('APPROVED');count(1,0)
            print('PASS 3: explicit owner action issues one approval, no enqueue')
            page.locator('#deny').click();expect(page.locator('#status')).to_have_text('DENIED');expect(page.locator('#allow')).to_be_disabled();count(1,0)
            print('PASS 4: simulated host denial never enqueues')
            page.locator('#device').select_option('ha');expect(page.locator('#status')).to_have_text('REVIEW');expect(page.locator('#task')).to_contain_text('"target": "ha"');expect(page.locator('#route option[value=legacy]')).to_be_disabled();expect(page.locator('#agree')).not_to_be_checked();approve();count(2,0)
            page.locator('#operation').select_option('exec');expect(page.locator('#status')).to_have_text('REVIEW');expect(page.locator('#agree')).not_to_be_checked();expect(page.locator('#allow')).to_be_disabled();count(2,0)
            print('PASS 5: operation change invalidates prior consent')
            approve();page.locator('#allow').click();expect(page.locator('#status')).to_have_text('QUEUED');expect(page.locator('#allow')).to_be_disabled();count(3,1)
            print('PASS 6: separate simulated host approval enqueues exactly once')
            page.locator('#device').select_option('keenetic');page.locator('#route').select_option('legacy');expect(page.locator('#task')).to_contain_text('"route": "legacy"');approve();page.locator('#cancel').click();expect(page.locator('#status')).to_have_text('CANCELLED');count(4,1)
            print('PASS 7: legacy client cancellation prevents enqueue')
            page.locator('#route').select_option('direct');approve();page.locator('#allow').click();expect(page.locator('#status')).to_have_text('QUEUED');count(5,2)
            print('PASS 8: direct synthetic client still requires explicit owner review')
            assert not outbound, outbound;assert not errors, errors
            page.screenshot(path=str(ROOT/'demo-preview.png'),full_page=True)
            print('PASS 9: no outbound requests or browser page errors')
            print('Chromium:',browser.version)
            browser.close()
    finally: server.shutdown();server.server_close();thread.join()
print('9/9 PASS (synthetic browser UI; NOT ChatGPT host confirmation)')
