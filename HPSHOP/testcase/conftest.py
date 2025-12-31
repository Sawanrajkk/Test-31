# testcase/conftest.py
# Robust conftest: make project root importable, prefer selinum.conftest fixtures,
# otherwise provide fallback driver and ss fixtures.

import os, sys

# ensure project root (one level up) is on sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Try to reuse fixtures from selinum.conftest if available
try:
    from selinum.conftest import driver, ss  # noqa: F401
except Exception:
    # Fallback fixtures for CI
    import pytest
    from selenium import webdriver

    @pytest.fixture(scope="function")
    def driver():
        options = webdriver.ChromeOptions()

        # Required for GitHub Actions (CI-safe)
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")

        # Pretend to be a real browser to bypass bot-detection
        options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )

        # Hide automation fingerprint
        options.add_argument("--disable-blink-features=AutomationControlled")

        prefs = {
            "profile.managed_default_content_settings.images": 1,
            "profile.default_content_setting_values.cookies": 1,
            "profile.default_content_setting_values.javascript": 1,
        }
        options.add_experimental_option("prefs", prefs)

        drv = webdriver.Chrome(options=options)

        # Remove navigator.webdriver=true
        drv.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            """
        })

        yield drv
        try:
            drv.quit()
        except Exception:
            pass

    @pytest.fixture(scope="function")
    def ss(request, driver):
        # simple screenshot helper that saves into ./screenshots/<testname>/
        import time
        from pathlib import Path
        import allure

        class SSHelper:
            def __init__(self):
                self.test_name = request.node.nodeid.replace("/", "_").replace("::", "_")
                self.seq = 0
                self.driver = driver
                self.root = Path(PROJECT_ROOT) / "screenshots"

            def _ensure(self):
                self.root.mkdir(parents=True, exist_ok=True)

            def take(self, step: str):
                self._ensure()
                self.seq += 1
                fname = f"{self.test_name}_{self.seq:02d}_{int(time.time())}_{step}.png"
                path = self.root / fname
                try:
                    driver.save_screenshot(str(path))
                except Exception:
                    try:
                        with open(path, "wb") as f:
                            f.write(driver.get_screenshot_as_png())
                    except Exception:
                        pass

                # attach to allure if possible
                try:
                    with open(path, "rb") as f:
                        allure.attach(f.read(), name=fname, attachment_type=allure.attachment_type.PNG)
                except Exception:
                    pass

                return str(path)

        return SSHelper()
