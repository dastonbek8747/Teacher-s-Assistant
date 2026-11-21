"""
AUTONOMOUS BROWSER AGENT TOOLS
================================
Playwright + LangChain Async Browser Tools (REAL GOOGLE CHROME)

Install:
    pip install playwright langchain-core
    playwright install chrome        # yoki Google Chrome allaqachon o'rnatilgan bo'lsin

IMPORTANT:
    These tools are ASYNC.
    Use agent.ainvoke(), not agent.invoke().

BROWSER MODES (.env orqali sozlanadi):

    BROWSER_MODE=persistent   (default)
        Playwright haqiqiy Google Chrome'ni o'zi ochadi va alohida profil
        papkasida ishlaydi. Login, cookie va sozlamalar keyingi ishga
        tushirishlarda saqlanadi.

    BROWSER_MODE=cdp
        Agent Chrome'ga remote debugging port orqali ulanadi. Chrome ishlamayotgan
        bo'lsa, u avtomatik ishga tushiriladi. Agent tugaganda Chrome yopilmaydi.

    Qo'shimcha o'zgaruvchilar (ixtiyoriy):
        BROWSER_CHANNEL=chrome                        (chrome | chrome-beta | msedge)
        CHROME_PROFILE_DIR=/home/user/.teachflow_browser_profile
        CHROME_CDP_URL=http://127.0.0.1:9222
        CHROME_PATH=/usr/bin/google-chrome            (faqat cdp rejimi uchun)
"""

import os
import re
import json
import shutil
import asyncio
import subprocess
import urllib.request

from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from playwright.async_api import (
    async_playwright,
    Browser,
    BrowserContext,
    Page,
)

from langchain_core.tools import tool


# ============================================================
# OUTPUT DIRECTORY
# ============================================================

# Barcha screenshot va yuklab olingan fayllar shu papkaga saqlanadi.
# Papka loyiha ishga tushirilgan joriy katalogga nisbatan aniqlanadi:
# ../creating_files/
CREATING_FILES_DIR = (Path.cwd() / "../creating_files").resolve()
CREATING_FILES_DIR.mkdir(parents=True, exist_ok=True)


def _output_path(path: str | Path) -> Path:
    """
    Berilgan yo'lni ../creating_files/ ichiga joylashtiradi.
    Absolute path berilsa ham fayl creating_files ichida saqlanadi.
    Path traversal (../../...) bloklanadi.
    """
    raw_path = Path(path).expanduser()

    if raw_path.is_absolute():
        raw_path = Path(raw_path.name)

    target = (CREATING_FILES_DIR / raw_path).resolve()

    if not target.is_relative_to(CREATING_FILES_DIR):
        raise ValueError("Fayl creating_files papkasidan tashqariga saqlanishi mumkin emas.")

    target.parent.mkdir(parents=True, exist_ok=True)
    return target


# ============================================================
# CONFIG
# ============================================================

def _browser_mode() -> str:
    mode = os.getenv("BROWSER_MODE", "persistent").strip().lower()
    return mode if mode in ("persistent", "cdp") else "persistent"


def _browser_channel() -> str:
    return os.getenv("BROWSER_CHANNEL", "chrome").strip() or "chrome"


def _profile_dir() -> str:
    default = str(Path.home() / ".teachflow_browser_profile")
    path = Path(os.getenv("CHROME_PROFILE_DIR", default)).expanduser()
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


def _cdp_url() -> str:
    return os.getenv("CHROME_CDP_URL", "http://127.0.0.1:9222").rstrip("/")


# Playwright avtomatlashtirish belgilarini kamaytiruvchi sozlamalar
CHROME_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--autoplay-policy=no-user-gesture-required",
    "--no-first-run",
    "--no-default-browser-check",
    "--start-maximized",
]


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def success(message: str, **kwargs) -> str:
    """Agentga standart JSON natija qaytaradi."""

    result = {
        "success": True,
        "message": message,
        **kwargs
    }

    return json.dumps(result, ensure_ascii=False, default=str)


def failure(tool_name: str, error: Exception) -> str:
    """Xatolikni standart JSON formatida qaytaradi."""

    return json.dumps(
        {
            "success": False,
            "tool": tool_name,
            "error_type": type(error).__name__,
            "error": str(error)
        },
        ensure_ascii=False
    )


def validate_url(url: str) -> str:
    """Faqat HTTP va HTTPS manzillariga ruxsat beradi."""

    url = url.strip()

    if url == "about:blank":
        return url

    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        raise ValueError("URL http:// yoki https:// bilan boshlanishi kerak.")

    if not parsed.netloc:
        raise ValueError("URL manzili noto'g'ri.")

    return url


def safe_filename(filename: str) -> str:
    """Fayl nomini xavfsiz formatga keltiradi."""

    filename = Path(filename).name
    filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", filename)

    return filename.strip(" .") or "downloaded_file"


def _find_chrome_binary() -> Optional[str]:
    """Tizimdagi Chrome ijro faylini topadi (cdp rejimi uchun)."""

    custom = os.getenv("CHROME_PATH")

    if custom and Path(custom).exists():
        return custom

    for name in (
            "google-chrome",
            "google-chrome-stable",
            "chrome",
            "chromium-browser",
            "chromium",
    ):
        found = shutil.which(name)

        if found:
            return found

    return None


async def _cdp_ready(url: str) -> bool:
    """Remote debugging port javob berayotganini tekshiradi."""

    def probe() -> bool:
        try:
            with urllib.request.urlopen(f"{url}/json/version", timeout=1) as r:
                return r.status == 200
        except Exception:
            return False

    return await asyncio.to_thread(probe)


async def _ensure_cdp_chrome(url: str) -> None:
    """Chrome debug portda ishlamayotgan bo'lsa, uni ishga tushiradi."""

    if await _cdp_ready(url):
        return

    binary = _find_chrome_binary()

    if not binary:
        raise RuntimeError(
            "Google Chrome topilmadi. Chrome o'rnating yoki "
            ".env ga CHROME_PATH=/to'liq/yo'l ni yozing."
        )

    port = urlparse(url).port or 9222

    subprocess.Popen(
        [
            binary,
            f"--remote-debugging-port={port}",
            f"--user-data-dir={_profile_dir()}",
            *CHROME_ARGS,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )

    for _ in range(40):
        await asyncio.sleep(0.5)

        if await _cdp_ready(url):
            return

    raise RuntimeError(
        f"Chrome ishga tushdi, lekin {url} javob bermayapti. "
        "Boshqa Chrome oynalari ochiq bo'lsa, ularni to'liq yoping."
    )


# ============================================================
# BROWSER MANAGER
# ============================================================

class BrowserManager:

    def __init__(self):

        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

        self.mode: Optional[str] = None
        self.context_closed = True

        self.downloaded_files = []
        self.lock = asyncio.Lock()

    def is_running(self) -> bool:

        if not self.context or self.context_closed:
            return False

        if self.browser is not None and not self.browser.is_connected():
            return False

        return True

    def _on_context_close(self, *_args):
        self.context_closed = True

    def _on_new_page(self, page: Page):
        """Havola yangi tabda ochilsa (target=_blank), agent shu tabga o'tadi."""
        self.page = page

    def attach_context(self, context: BrowserContext):

        self.context = context
        self.context_closed = False

        context.on("close", self._on_context_close)
        context.on("page", self._on_new_page)

    async def get_page(self) -> Page:

        if not self.is_running():
            raise RuntimeError(
                "Browser ishga tushmagan yoki yopilgan. "
                "Avval start_browser chaqiring."
            )

        if self.page is None or self.page.is_closed():

            pages = [p for p in self.context.pages if not p.is_closed()]

            if pages:
                self.page = pages[-1]
            else:
                self.page = await self.context.new_page()

        return self.page

    async def get_context(self) -> BrowserContext:

        if not self.is_running():
            raise RuntimeError("Browser context mavjud emas.")

        return self.context

    async def close(self):
        """
        persistent rejim: Chrome oynasi yopiladi.
        cdp rejim: faqat ulanish uziladi, Chrome ochiq qoladi.
        """

        if self.mode == "persistent" and self.context:

            try:
                await self.context.close()
            except Exception:
                pass

        elif self.browser:

            # CDP: browser.close() foydalanuvchi Chrome'ini yopmaydi,
            # faqat Playwright ulanishini uzadi.
            try:
                if self.browser.is_connected():
                    await self.browser.close()
            except Exception:
                pass

        if self.playwright:

            try:
                await self.playwright.stop()
            except Exception:
                pass

        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None
        self.mode = None
        self.context_closed = True


browser_manager = BrowserManager()


async def shutdown_browser() -> None:
    """Dastur oxirida chaqiriladi (tool emas, oddiy async funksiya)."""
    await browser_manager.close()


# ============================================================
# 1. START BROWSER
# ============================================================

@tool
async def start_browser(headless: bool = False) -> str:
    """
    Haqiqiy Google Chrome brauzerini ishga tushiradi (yoki ochiq Chrome'ga ulanadi).

    headless=False:
        Brauzer oynasi ko'rinadi (tavsiya etiladi).

    headless=True:
        Brauzer fonda ishlaydi.
    """

    try:

        async with browser_manager.lock:

            if browser_manager.is_running():
                page = await browser_manager.get_page()

                return success(
                    "Browser allaqachon ishga tushirilgan.",
                    url=page.url,
                    mode=browser_manager.mode
                )

            await browser_manager.close()

            mode = _browser_mode()

            browser_manager.playwright = await async_playwright().start()

            if mode == "cdp":

                url = _cdp_url()

                await _ensure_cdp_chrome(url)

                browser_manager.browser = (
                    await browser_manager.playwright.chromium.connect_over_cdp(url)
                )

                context = (
                    browser_manager.browser.contexts[0]
                    if browser_manager.browser.contexts
                    else await browser_manager.browser.new_context()
                )

            else:

                context = (
                    await browser_manager.playwright.chromium
                    .launch_persistent_context(
                        user_data_dir=_profile_dir(),
                        channel=_browser_channel(),
                        headless=headless,
                        viewport=None,
                        accept_downloads=True,
                        ignore_default_args=["--enable-automation"],
                        args=CHROME_ARGS,
                    )
                )

            browser_manager.mode = mode
            browser_manager.attach_context(context)

            pages = [p for p in context.pages if not p.is_closed()]

            browser_manager.page = (
                pages[0] if pages else await context.new_page()
            )

            browser_manager.downloaded_files.clear()

            return success(
                "Haqiqiy Chrome muvaffaqiyatli ishga tushdi.",
                mode=mode,
                channel=_browser_channel() if mode == "persistent" else "cdp",
                headless=headless if mode == "persistent" else False,
                profile_dir=_profile_dir()
            )

    except Exception as e:

        await browser_manager.close()

        error_text = str(e)

        if "Executable doesn't exist" in error_text or "distribution" in error_text:
            error_text += (
                " | Yechim: terminalda `playwright install chrome` ni bajaring."
            )

        return json.dumps(
            {
                "success": False,
                "tool": "start_browser",
                "error_type": type(e).__name__,
                "error": error_text
            },
            ensure_ascii=False
        )


# ============================================================
# 2. CLOSE BROWSER
# ============================================================

@tool
async def close_browser() -> str:
    """Brauzer va Playwright resurslarini yopadi."""

    try:

        await browser_manager.close()

        return success("Browser yopildi.")

    except Exception as e:

        return failure("close_browser", e)


# ============================================================
# 3. NAVIGATE TO URL
# ============================================================

@tool
async def navigate_to_url(
        url: str,
        wait_until: str = "domcontentloaded"
) -> str:
    """
    Berilgan URL manzilga o'tadi.

    wait_until:
        load
        domcontentloaded
        networkidle
        commit
    """

    try:

        url = validate_url(url)

        if wait_until not in ["load", "domcontentloaded", "networkidle", "commit"]:
            raise ValueError("wait_until noto'g'ri.")

        page = await browser_manager.get_page()

        response = await page.goto(url, wait_until=wait_until, timeout=60000)

        return success(
            "Sahifaga o'tildi.",
            url=page.url,
            title=await page.title(),
            status=response.status if response else None
        )

    except Exception as e:

        return failure("navigate_to_url", e)


# ============================================================
# 4. GO BACK
# ============================================================

@tool
async def go_back() -> str:
    """Oldingi sahifaga qaytadi."""

    try:

        page = await browser_manager.get_page()

        response = await page.go_back(wait_until="domcontentloaded", timeout=30000)

        return success(
            "Orqaga qaytildi." if response else "Oldingi sahifa yo'q.",
            url=page.url,
            title=await page.title()
        )

    except Exception as e:

        return failure("go_back", e)


# ============================================================
# 5. GO FORWARD
# ============================================================

@tool
async def go_forward() -> str:
    """Keyingi sahifaga o'tadi."""

    try:

        page = await browser_manager.get_page()

        response = await page.go_forward(wait_until="domcontentloaded", timeout=30000)

        return success(
            "Oldinga o'tildi." if response else "Keyingi sahifa yo'q.",
            url=page.url,
            title=await page.title()
        )

    except Exception as e:

        return failure("go_forward", e)


# ============================================================
# 6. RELOAD PAGE
# ============================================================

@tool
async def reload_page() -> str:
    """Joriy sahifani qayta yuklaydi."""

    try:

        page = await browser_manager.get_page()

        response = await page.reload(wait_until="domcontentloaded", timeout=60000)

        return success(
            "Sahifa qayta yuklandi.",
            url=page.url,
            status=response.status if response else None
        )

    except Exception as e:

        return failure("reload_page", e)


# ============================================================
# 7. GET PAGE INFO
# ============================================================

@tool
async def get_page_info() -> str:
    """Joriy sahifaning asosiy ma'lumotlarini oladi."""

    try:

        page = await browser_manager.get_page()
        context = await browser_manager.get_context()

        return success(
            "Sahifa ma'lumotlari.",
            url=page.url,
            title=await page.title(),
            is_closed=page.is_closed(),
            total_tabs=len(context.pages),
            mode=browser_manager.mode
        )

    except Exception as e:

        return failure("get_page_info", e)


# ============================================================
# 8. GET PAGE CONTENT
# ============================================================

@tool
async def get_page_content(max_chars: int = 15000) -> str:
    """Sahifadagi ko'rinadigan matnlarni oladi."""

    try:

        if max_chars < 1:
            raise ValueError("max_chars kamida 1 bo'lishi kerak.")

        page = await browser_manager.get_page()

        content = await page.locator("body").inner_text(timeout=20000)

        return success(
            "Sahifa matni olindi.",
            url=page.url,
            content=content[:max_chars],
            total_chars=len(content),
            truncated=len(content) > max_chars
        )

    except Exception as e:

        return failure("get_page_content", e)


# ============================================================
# 9. GET PAGE HTML
# ============================================================

@tool
async def get_page_html(max_chars: int = 20000) -> str:
    """Sahifaning HTML kodini oladi."""

    try:

        if max_chars < 1:
            raise ValueError("max_chars kamida 1 bo'lishi kerak.")

        page = await browser_manager.get_page()

        html = await page.content()

        return success(
            "HTML olindi.",
            url=page.url,
            html=html[:max_chars],
            total_chars=len(html),
            truncated=len(html) > max_chars
        )

    except Exception as e:

        return failure("get_page_html", e)


# ============================================================
# 10. TAKE SCREENSHOT
# ============================================================

@tool
async def take_screenshot(
        path: str = "screenshots/browser.png",
        full_page: bool = False
) -> str:
    """Brauzer sahifasidan screenshot oladi."""

    try:

        page = await browser_manager.get_page()

        file_path = _output_path(path)

        await page.screenshot(path=str(file_path), full_page=full_page)

        return success(
            "Screenshot saqlandi.",
            path=str(file_path.resolve()),
            url=page.url
        )

    except Exception as e:

        return failure("take_screenshot", e)


# ============================================================
# 11. CLICK ELEMENT
# ============================================================

@tool
async def click_element(
        selector: str,
        timeout: int = 15000
) -> str:
    """
    Selector orqali elementni bosadi.

    Selector turlari:
        CSS:        button.submit
        Matn:       text=Kirish
        Rol:        role=button[name="Search"]
        Aniq matn:  text="Play"
    """

    try:

        page = await browser_manager.get_page()

        await page.locator(selector).first.click(timeout=timeout)

        return success(
            "Element bosildi.",
            selector=selector,
            url=page.url
        )

    except Exception as e:

        return failure("click_element", e)


# ============================================================
# 12. FILL INPUT
# ============================================================

@tool
async def fill_input(
        selector: str,
        value: str,
        timeout: int = 15000
) -> str:
    """Input yoki textarea maydonini to'ldiradi."""

    try:

        page = await browser_manager.get_page()

        await page.locator(selector).first.fill(value, timeout=timeout)

        return success("Input to'ldirildi.", selector=selector)

    except Exception as e:

        return failure("fill_input", e)


# ============================================================
# 13. TYPE TEXT
# ============================================================

@tool
async def type_text(
        selector: str,
        text: str,
        delay: int = 50
) -> str:
    """Matnni harflab yozadi."""

    try:

        if delay < 0:
            raise ValueError("delay manfiy bo'lmasligi kerak.")

        page = await browser_manager.get_page()

        await page.locator(selector).first.press_sequentially(text, delay=delay)

        return success("Matn yozildi.", selector=selector, characters=len(text))

    except Exception as e:

        return failure("type_text", e)


# ============================================================
# 14. PRESS KEY
# ============================================================

@tool
async def press_key(
        selector: str,
        key: str
) -> str:
    """Elementda klaviatura tugmasini bosadi (masalan: Enter, Escape, Space)."""

    try:

        page = await browser_manager.get_page()

        await page.locator(selector).first.press(key)

        return success("Tugma bosildi.", selector=selector, key=key)

    except Exception as e:

        return failure("press_key", e)


# ============================================================
# 15. SELECT OPTION
# ============================================================

@tool
async def select_option(
        selector: str,
        value: str
) -> str:
    """HTML select elementidan variant tanlaydi."""

    try:

        page = await browser_manager.get_page()

        selected = await page.locator(selector).first.select_option(value=value)

        return success("Variant tanlandi.", selector=selector, selected=selected)

    except Exception as e:

        return failure("select_option", e)


# ============================================================
# 16. CHECK CHECKBOX
# ============================================================

@tool
async def check_checkbox(selector: str) -> str:
    """Checkbox yoki radio elementini belgilaydi."""

    try:

        page = await browser_manager.get_page()

        await page.locator(selector).first.check()

        return success("Element belgilandi.", selector=selector)

    except Exception as e:

        return failure("check_checkbox", e)


# ============================================================
# 17. UNCHECK CHECKBOX
# ============================================================

@tool
async def uncheck_checkbox(selector: str) -> str:
    """Checkbox belgisini olib tashlaydi."""

    try:

        page = await browser_manager.get_page()

        await page.locator(selector).first.uncheck()

        return success("Checkbox belgisi olib tashlandi.", selector=selector)

    except Exception as e:

        return failure("uncheck_checkbox", e)


# ============================================================
# 18. HOVER ELEMENT
# ============================================================

@tool
async def hover_element(selector: str) -> str:
    """Kursorni element ustiga olib boradi."""

    try:

        page = await browser_manager.get_page()

        await page.locator(selector).first.hover()

        return success("Hover bajarildi.", selector=selector)

    except Exception as e:

        return failure("hover_element", e)


# ============================================================
# 19. SCROLL PAGE
# ============================================================

@tool
async def scroll_page(
        direction: str = "down",
        amount: int = 600
) -> str:
    """Sahifani yuqoriga yoki pastga aylantiradi."""

    try:

        if direction not in ["up", "down"]:
            raise ValueError("direction up yoki down bo'lishi kerak.")

        if amount < 0:
            raise ValueError("amount manfiy bo'lmasligi kerak.")

        page = await browser_manager.get_page()

        distance = amount if direction == "down" else -amount

        scroll_y = await page.evaluate(
            """
            distance => {
                window.scrollBy(0, distance);
                return window.scrollY;
            }
            """,
            distance
        )

        return success("Scroll bajarildi.", direction=direction, scroll_y=scroll_y)

    except Exception as e:

        return failure("scroll_page", e)


# ============================================================
# 20. SCROLL TO ELEMENT
# ============================================================

@tool
async def scroll_to_element(selector: str) -> str:
    """Element ko'rinadigan joygacha scroll qiladi."""

    try:

        page = await browser_manager.get_page()

        await page.locator(selector).first.scroll_into_view_if_needed()

        return success("Elementga scroll qilindi.", selector=selector)

    except Exception as e:

        return failure("scroll_to_element", e)


# ============================================================
# 21. WAIT FOR ELEMENT
# ============================================================

@tool
async def wait_for_element(
        selector: str,
        state: str = "visible",
        timeout: int = 15000
) -> str:
    """Element holatini kutadi."""

    try:

        if state not in ["visible", "hidden", "attached", "detached"]:
            raise ValueError("Noto'g'ri state.")

        page = await browser_manager.get_page()

        await page.locator(selector).first.wait_for(state=state, timeout=timeout)

        return success(
            "Element holati tasdiqlandi.",
            selector=selector,
            state=state
        )

    except Exception as e:

        return failure("wait_for_element", e)


# ============================================================
# 22. GET ALL LINKS
# ============================================================

@tool
async def get_all_links(limit: int = 200) -> str:
    """Sahifadagi barcha havolalarni oladi."""

    try:

        page = await browser_manager.get_page()

        links = await page.locator("a").evaluate_all(
            """
            elements => elements.map((a, index) => ({
                index,
                text: (a.innerText || a.getAttribute('aria-label') || '').trim(),
                href: a.href
            })).filter(item => item.href)
            """
        )

        return success("Havolalar olindi.", links=links[:limit], total=len(links))

    except Exception as e:

        return failure("get_all_links", e)


# ============================================================
# 23. GET ALL BUTTONS
# ============================================================

@tool
async def get_all_buttons(limit: int = 200) -> str:
    """Sahifadagi barcha buttonlarni aniqlaydi."""

    try:

        page = await browser_manager.get_page()

        buttons = await page.locator(
            "button, input[type=submit], input[type=button], [role=button]"
        ).evaluate_all(
            """
            elements => elements.map((el, index) => ({
                index,
                text: (
                    el.innerText ||
                    el.value ||
                    el.getAttribute('aria-label') ||
                    ''
                ).trim(),
                type: el.getAttribute('type'),
                disabled: !!el.disabled,
                ariaLabel: el.getAttribute('aria-label')
            }))
            """
        )

        return success("Buttonlar olindi.", buttons=buttons[:limit], total=len(buttons))

    except Exception as e:

        return failure("get_all_buttons", e)


# ============================================================
# 24. GET ALL INPUTS
# ============================================================

@tool
async def get_all_inputs(limit: int = 200) -> str:
    """Input, textarea va select elementlarini oladi. Maxfiy qiymatlar yashiriladi."""

    try:

        page = await browser_manager.get_page()

        inputs = await page.locator("input, textarea, select").evaluate_all(
            """
            elements => elements.map((el, index) => {
                const type = (el.type || '').toLowerCase();
                const sensitive = ['password', 'hidden'].includes(type);

                return {
                    index,
                    tag: el.tagName.toLowerCase(),
                    type: type || null,
                    name: el.name || null,
                    id: el.id || null,
                    placeholder: el.placeholder || null,
                    value: sensitive ? '[HIDDEN]' : (el.value || ''),
                    required: !!el.required,
                    disabled: !!el.disabled,
                    ariaLabel: el.getAttribute('aria-label')
                };
            })
            """
        )

        return success("Inputlar olindi.", inputs=inputs[:limit], total=len(inputs))

    except Exception as e:

        return failure("get_all_inputs", e)


# ============================================================
# 25. GET ELEMENT TEXT
# ============================================================

@tool
async def get_element_text(
        selector: str,
        max_chars: int = 10000
) -> str:
    """Belgilangan elementning matnini oladi."""

    try:

        page = await browser_manager.get_page()

        text = await page.locator(selector).first.inner_text()

        return success(
            "Element matni olindi.",
            selector=selector,
            text=text[:max_chars],
            truncated=len(text) > max_chars
        )

    except Exception as e:

        return failure("get_element_text", e)


# ============================================================
# 26. GET ELEMENT ATTRIBUTE
# ============================================================

@tool
async def get_element_attribute(
        selector: str,
        attribute: str
) -> str:
    """Element atributini oladi."""

    try:

        page = await browser_manager.get_page()

        value = await page.locator(selector).first.get_attribute(attribute)

        return success(
            "Atribut olindi.",
            selector=selector,
            attribute=attribute,
            value=value
        )

    except Exception as e:

        return failure("get_element_attribute", e)


# ============================================================
# 27. OPEN NEW TAB
# ============================================================

@tool
async def open_new_tab(url: str = "about:blank") -> str:
    """Yangi tab ochadi va uni faol qiladi."""

    try:

        url = validate_url(url)

        context = await browser_manager.get_context()

        page = await context.new_page()

        browser_manager.page = page

        if url != "about:blank":
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)

        return success(
            "Yangi tab ochildi.",
            url=page.url,
            title=await page.title()
        )

    except Exception as e:

        return failure("open_new_tab", e)


# ============================================================
# 28. SWITCH TAB
# ============================================================

@tool
async def switch_tab(index: int) -> str:
    """Tab indeksiga qarab boshqa tabga o'tadi."""

    try:

        context = await browser_manager.get_context()

        pages = [p for p in context.pages if not p.is_closed()]

        if index < 0 or index >= len(pages):
            raise IndexError(f"Tab topilmadi. Ochiq tablar: {len(pages)}")

        browser_manager.page = pages[index]

        await browser_manager.page.bring_to_front()

        return success(
            "Tab almashtirildi.",
            index=index,
            url=browser_manager.page.url,
            title=await browser_manager.page.title()
        )

    except Exception as e:

        return failure("switch_tab", e)


# ============================================================
# 29. GET ALL TABS
# ============================================================

@tool
async def get_all_tabs() -> str:
    """Ochiq tablar ro'yxatini beradi."""

    try:

        context = await browser_manager.get_context()

        tabs = []

        open_pages = [p for p in context.pages if not p.is_closed()]

        for index, page in enumerate(open_pages):
            tabs.append({
                "index": index,
                "url": page.url,
                "title": await page.title(),
                "active": page == browser_manager.page
            })

        return success("Tablar ro'yxati olindi.", tabs=tabs, total=len(tabs))

    except Exception as e:

        return failure("get_all_tabs", e)


# ============================================================
# 30. CLOSE TAB
# ============================================================

@tool
async def close_tab(index: int) -> str:
    """Berilgan indeksdagi tabni yopadi."""

    try:

        context = await browser_manager.get_context()

        pages = [p for p in context.pages if not p.is_closed()]

        if index < 0 or index >= len(pages):
            raise IndexError("Tab topilmadi.")

        if len(pages) == 1:
            raise RuntimeError("Oxirgi tabni yopib bo'lmaydi.")

        target = pages[index]

        was_active = target == browser_manager.page

        await target.close()

        remaining = [p for p in context.pages if not p.is_closed()]

        if was_active:
            browser_manager.page = remaining[-1]

        return success(
            "Tab yopildi.",
            closed_index=index,
            active_url=browser_manager.page.url
        )

    except Exception as e:

        return failure("close_tab", e)


# ============================================================
# 31. UPLOAD FILE
# ============================================================

@tool
async def upload_file(
        selector: str,
        file_path: str
) -> str:
    """Saytdagi file input orqali fayl yuklaydi."""

    try:

        path = Path(file_path).expanduser().resolve()

        if not path.is_file():
            raise FileNotFoundError(f"Fayl topilmadi: {path}")

        page = await browser_manager.get_page()

        await page.locator(selector).first.set_input_files(str(path))

        return success(
            "Fayl inputga biriktirildi.",
            file_path=str(path),
            selector=selector
        )

    except Exception as e:

        return failure("upload_file", e)


# ============================================================
# 32. DOWNLOAD FILE
# ============================================================

@tool
async def download_file(
        selector: str,
        save_path: str = "downloads"
) -> str:
    """Tugma yoki havolani bosib faylni yuklab oladi."""

    try:

        page = await browser_manager.get_page()

        folder = _output_path(save_path)
        folder.mkdir(parents=True, exist_ok=True)

        async with page.expect_download(timeout=60000) as download_info:
            await page.locator(selector).first.click(timeout=20000)

        download = await download_info.value

        filename = safe_filename(download.suggested_filename)

        file_path = (folder / filename).resolve()

        await download.save_as(str(file_path))

        browser_manager.downloaded_files.append(str(file_path))

        return success(
            "Fayl yuklab olindi.",
            path=str(file_path),
            filename=filename
        )

    except Exception as e:

        return failure("download_file", e)


# ============================================================
# 33. GET DOWNLOADED FILES
# ============================================================

@tool
async def get_downloaded_files() -> str:
    """Yuklab olingan fayllar ro'yxatini beradi."""

    try:

        files = [
            path
            for path in browser_manager.downloaded_files
            if Path(path).exists()
        ]

        return success("Yuklangan fayllar ro'yxati.", files=files, total=len(files))

    except Exception as e:

        return failure("get_downloaded_files", e)


# ============================================================
# 34. WAIT FOR PAGE LOAD
# ============================================================

@tool
async def wait_for_page_load(
        state: str = "domcontentloaded",
        timeout: int = 30000
) -> str:
    """Sahifa yuklanish holatini kutadi."""

    try:

        if state not in ["load", "domcontentloaded", "networkidle"]:
            raise ValueError("Noto'g'ri state.")

        page = await browser_manager.get_page()

        await page.wait_for_load_state(state, timeout=timeout)

        return success("Sahifa yuklandi.", state=state, url=page.url)

    except Exception as e:

        return failure("wait_for_page_load", e)


# ============================================================
# 35. SEARCH TEXT ON PAGE
# ============================================================

@tool
async def search_text_on_page(
        query: str,
        case_sensitive: bool = False
) -> str:
    """Joriy sahifa ichidan kerakli matnni qidiradi."""

    try:

        page = await browser_manager.get_page()

        content = await page.locator("body").inner_text()

        source = content if case_sensitive else content.casefold()
        search = query if case_sensitive else query.casefold()

        index = source.find(search)

        if index == -1:
            return success("Matn topilmadi.", query=query, found=False)

        start = max(0, index - 250)
        end = min(len(content), index + len(query) + 500)

        return success(
            "Matn topildi.",
            query=query,
            found=True,
            position=index,
            excerpt=content[start:end]
        )

    except Exception as e:

        return failure("search_text_on_page", e)


# ============================================================
# 36. GET PAGE METADATA
# ============================================================

@tool
async def get_page_metadata() -> str:
    """Title, description, canonical va Open Graph metadata oladi."""

    try:

        page = await browser_manager.get_page()

        metadata = await page.evaluate(
            """
            () => {
                const get = (selector, attr = "content") =>
                    document.querySelector(selector)?.getAttribute(attr) || null;

                return {
                    title: document.title || null,
                    description: get('meta[name="description"]'),
                    canonical: get('link[rel="canonical"]', 'href'),
                    ogTitle: get('meta[property="og:title"]'),
                    ogDescription: get('meta[property="og:description"]'),
                    ogUrl: get('meta[property="og:url"]'),
                    language: document.documentElement.lang || null
                };
            }
            """
        )

        return success("Metadata olindi.", url=page.url, metadata=metadata)

    except Exception as e:

        return failure("get_page_metadata", e)


# ============================================================
# 37. GET VISIBLE TEXT SUMMARY
# ============================================================

@tool
async def get_visible_text_summary(max_chars: int = 8000) -> str:
    """Sahifa matnini ixcham ko'rinishda qaytaradi."""

    try:

        page = await browser_manager.get_page()

        content = await page.locator("body").inner_text()

        lines = [line.strip() for line in content.splitlines() if line.strip()]

        compact = "\n".join(lines)

        return success(
            "Sahifa matni ixchamlandi.",
            url=page.url,
            text=compact[:max_chars],
            total_chars=len(compact),
            truncated=len(compact) > max_chars
        )

    except Exception as e:

        return failure("get_visible_text_summary", e)



# ============================================================
# 38. TAKE ELEMENT SCREENSHOT
# ============================================================

@tool
async def take_element_screenshot(
        selector: str,
        path: str = "screenshots/element.png"
) -> str:
    """Faqat tanlangan HTML elementdan screenshot oladi."""
    try:
        page = await browser_manager.get_page()
        element = page.locator(selector).first
        await element.wait_for(state="visible", timeout=15000)
        file_path = _output_path(path)
        await element.screenshot(path=str(file_path))
        return success(
            "Element screenshot saqlandi.",
            path=str(file_path),
            selector=selector,
            url=page.url
        )
    except Exception as e:
        return failure("take_element_screenshot", e)


# ============================================================
# 39. SAVE PAGE AS PDF
# ============================================================

@tool
async def save_page_as_pdf(
        path: str = "pdf/page.pdf",
        print_background: bool = True,
        landscape: bool = False
) -> str:
    """Joriy sahifani PDF formatida creating_files ichiga saqlaydi."""
    try:
        page = await browser_manager.get_page()
        file_path = _output_path(path)
        await page.pdf(
            path=str(file_path),
            print_background=print_background,
            landscape=landscape,
            prefer_css_page_size=True
        )
        return success("Sahifa PDF sifatida saqlandi.", path=str(file_path), url=page.url)
    except Exception as e:
        return failure("save_page_as_pdf", e)


# ============================================================
# 40. EXTRACT HTML TABLES
# ============================================================

@tool
async def get_page_tables(max_tables: int = 20, max_rows: int = 100) -> str:
    """Sahifadagi HTML jadvallarni sarlavha va qatorlari bilan ajratib oladi."""
    try:
        page = await browser_manager.get_page()
        tables = await page.locator("table").evaluate_all(
            """(els) => els.map((table, tableIndex) => ({
                tableIndex,
                caption: table.caption?.innerText?.trim() || null,
                headers: Array.from(table.querySelectorAll("thead th"))
                    .map(x => x.innerText.trim()),
                rows: Array.from(table.querySelectorAll("tr")).slice(0, 100)
                    .map(row => Array.from(row.querySelectorAll("th, td"))
                        .map(cell => cell.innerText.trim()))
            }))"""
        )
        tables = tables[:max(0, max_tables)]
        for table in tables:
            table["rows"] = table["rows"][:max(0, max_rows)]
        return success("Sahifa jadvallari olindi.", url=page.url, tables=tables, total=len(tables))
    except Exception as e:
        return failure("get_page_tables", e)


# ============================================================
# 41. EXTRACT PAGE IMAGES
# ============================================================

@tool
async def get_page_images(limit: int = 100) -> str:
    """Sahifadagi rasm manzillari, alt matni va o'lchamlarini oladi."""
    try:
        page = await browser_manager.get_page()
        images = await page.locator("img").evaluate_all(
            """els => els.map((img, index) => ({
                index,
                src: img.currentSrc || img.src || null,
                alt: img.alt || null,
                width: img.naturalWidth || img.width || null,
                height: img.naturalHeight || img.height || null,
                visible: !!(img.offsetWidth || img.offsetHeight)
            }))"""
        )
        return success("Rasmlar ro'yxati olindi.", url=page.url, images=images[:max(0, limit)], total=len(images))
    except Exception as e:
        return failure("get_page_images", e)


# ============================================================
# 42. EXTRACT PAGE FORMS
# ============================================================

@tool
async def get_page_forms(limit: int = 50) -> str:
    """Sahifadagi formalar va ularning maydonlarini tahlil qiladi."""
    try:
        page = await browser_manager.get_page()
        forms = await page.locator("form").evaluate_all(
            """forms => forms.map((form, index) => ({
                index,
                action: form.action || null,
                method: (form.method || "get").toUpperCase(),
                fields: Array.from(form.querySelectorAll("input, textarea, select, button"))
                    .map(el => ({
                        tag: el.tagName.toLowerCase(),
                        type: el.type || null,
                        name: el.name || null,
                        id: el.id || null,
                        placeholder: el.placeholder || null,
                        required: !!el.required,
                        disabled: !!el.disabled
                    }))
            }))"""
        )
        return success("Formalar olindi.", url=page.url, forms=forms[:max(0, limit)], total=len(forms))
    except Exception as e:
        return failure("get_page_forms", e)


# ============================================================
# 43. FIND ELEMENTS
# ============================================================

@tool
async def find_elements(
        selector: str,
        limit: int = 50
) -> str:
    """CSS selector bo'yicha elementlarni topadi va qisqa ma'lumot beradi."""
    try:
        page = await browser_manager.get_page()
        locator = page.locator(selector)
        total = await locator.count()
        elements = await locator.evaluate_all(
            """els => els.slice(0, 200).map((el, index) => ({
                index,
                tag: el.tagName.toLowerCase(),
                text: (el.innerText || el.textContent || "").trim().slice(0, 500),
                id: el.id || null,
                className: typeof el.className === "string" ? el.className : null,
                href: el.href || null,
                visible: !!(el.offsetWidth || el.offsetHeight),
                disabled: !!el.disabled
            }))"""
        )
        return success(
            "Elementlar qidirildi.",
            selector=selector,
            elements=elements[:max(0, limit)],
            total=total
        )
    except Exception as e:
        return failure("find_elements", e)


# ============================================================
# 44. CLEAR INPUT
# ============================================================

@tool
async def clear_input(selector: str) -> str:
    """Input yoki textarea ichidagi matnni tozalaydi."""
    try:
        page = await browser_manager.get_page()
        await page.locator(selector).first.clear(timeout=15000)
        return success("Input tozalandi.", selector=selector)
    except Exception as e:
        return failure("clear_input", e)


# ============================================================
# 45. PRESS PAGE KEY
# ============================================================

@tool
async def press_page_key(key: str) -> str:
    """Klaviatura tugmasini joriy sahifada bosadi. Masalan: Escape, Enter, Control+L."""
    try:
        page = await browser_manager.get_page()
        await page.keyboard.press(key)
        return success("Klaviatura tugmasi bosildi.", key=key, url=page.url)
    except Exception as e:
        return failure("press_page_key", e)


# ============================================================
# 46. GET PAGE PERFORMANCE
# ============================================================

@tool
async def get_page_performance() -> str:
    """Sahifa yuklanish va resurslar bo'yicha Performance API ma'lumotlarini oladi."""
    try:
        page = await browser_manager.get_page()
        metrics = await page.evaluate(
            """() => {
                const nav = performance.getEntriesByType("navigation")[0];
                const resources = performance.getEntriesByType("resource");
                return {
                    navigation: nav ? {
                        domContentLoaded: nav.domContentLoadedEventEnd,
                        loadEvent: nav.loadEventEnd,
                        responseTime: nav.responseEnd - nav.requestStart,
                        totalDuration: nav.duration
                    } : null,
                    resourceCount: resources.length,
                    transferSize: resources.reduce((sum, r) => sum + (r.transferSize || 0), 0),
                    resourceTypes: resources.reduce((acc, r) => {
                        const type = (r.initiatorType || "other");
                        acc[type] = (acc[type] || 0) + 1;
                        return acc;
                    }, {})
                };
            }"""
        )
        return success("Performance ma'lumotlari olindi.", url=page.url, metrics=metrics)
    except Exception as e:
        return failure("get_page_performance", e)


# ============================================================
# 47. GET PAGE LINKS BY TEXT
# ============================================================

@tool
async def get_links_by_text(
        query: str,
        limit: int = 50,
        case_sensitive: bool = False
) -> str:
    """Havolalarni matni bo'yicha qidiradi."""
    try:
        page = await browser_manager.get_page()
        links = await page.locator("a").evaluate_all(
            """els => els.map(a => ({
                text: (a.innerText || a.getAttribute("aria-label") || "").trim(),
                href: a.href || null,
                title: a.title || null
            })).filter(a => a.href)"""
        )
        needle = query if case_sensitive else query.casefold()
        matched = [
            item for item in links
            if needle in (item["text"] if case_sensitive else item["text"].casefold())
        ]
        return success(
            "Mos havolalar topildi.",
            query=query,
            links=matched[:max(0, limit)],
            total=len(matched)
        )
    except Exception as e:
        return failure("get_links_by_text", e)


# ============================================================
# 48. DOWNLOAD URL DIRECTLY
# ============================================================

@tool
async def download_url(
        url: str,
        filename: str = ""
) -> str:
    """URL manzilidagi faylni brauzer sessiyasi orqali creating_files ichiga yuklaydi."""
    try:
        url = validate_url(url)
        context = await browser_manager.get_context()
        response = await context.request.get(url, timeout=60000)
        if not response.ok:
            raise RuntimeError(f"Yuklab olish muvaffaqiyatsiz. HTTP status: {response.status}")

        suggested = filename.strip() or Path(urlparse(url).path).name or "downloaded_file"
        safe_name = safe_filename(suggested)
        file_path = _output_path(safe_name)
        body = await response.body()
        file_path.write_bytes(body)
        browser_manager.downloaded_files.append(str(file_path))

        return success(
            "URL orqali fayl yuklab olindi.",
            url=url,
            path=str(file_path),
            filename=safe_name,
            size_bytes=len(body),
            status=response.status
        )
    except Exception as e:
        return failure("download_url", e)



# ============================================================
# ALL BROWSER TOOLS
# ============================================================

BROWSER_TOOLS = [

    start_browser,
    close_browser,

    navigate_to_url,
    go_back,
    go_forward,
    reload_page,

    get_page_info,
    get_page_content,
    get_page_html,
    take_screenshot,

    click_element,
    fill_input,
    type_text,
    press_key,
    select_option,

    check_checkbox,
    uncheck_checkbox,
    hover_element,

    scroll_page,
    scroll_to_element,
    wait_for_element,

    get_all_links,
    get_all_buttons,
    get_all_inputs,

    get_element_text,
    get_element_attribute,

    open_new_tab,
    switch_tab,
    get_all_tabs,
    close_tab,

    upload_file,
    download_file,
    get_downloaded_files,

    wait_for_page_load,
    search_text_on_page,
    get_page_metadata,
    get_visible_text_summary,

    # Qo'shimcha 10 ta professional browser tool
    take_element_screenshot,
    save_page_as_pdf,
    get_page_tables,
    get_page_images,
    get_page_forms,
    find_elements,
    clear_input,
    press_page_key,
    get_page_performance,
    get_links_by_text,
    download_url,

]
