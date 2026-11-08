"""Offline Chromium DOM smoke tests (no localhost or public network required)."""
import os
import unittest

@unittest.skipUnless(os.environ.get('CITE_CHECK_TEST_BROWSER') == '1',
                     'Set CITE_CHECK_TEST_BROWSER=1 for real browser DOM tests')
class BrowserDOMTests(unittest.TestCase):
    def setUp(self):
        from playwright.sync_api import sync_playwright
        self.ctx = sync_playwright().start()
        opts = {'headless': True}
        if os.environ.get('CITE_CHECK_BROWSER_PATH'):
            opts['executable_path'] = os.environ['CITE_CHECK_BROWSER_PATH']
        self.browser = self.ctx.chromium.launch(**opts)
        self.page = self.browser.new_page()

    def tearDown(self):
        self.browser.close()
        self.ctx.stop()

    def test_inline_javascript_renders(self):
        self.page.set_content('<div id="result"></div><script>setTimeout(() => {document.querySelector("#result").textContent="Sentetik hukuk metni"},100)</script>')
        self.page.get_by_text('Sentetik hukuk metni').wait_for()
        self.assertEqual(self.page.locator('#result').inner_text(),'Sentetik hukuk metni')

    def test_form_fill_and_click(self):
        self.page.set_content('<input id="term"><button onclick="document.querySelector(\'#result\').textContent=document.querySelector(\'#term\').value">Ara</button><div id="result"></div>')
        self.page.locator('#term').fill('4857')
        self.page.get_by_role('button',name='Ara').click()
        self.assertEqual(self.page.locator('#result').inner_text(),'4857')

if __name__ == '__main__':
    unittest.main()
