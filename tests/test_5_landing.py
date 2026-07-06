"""Функция 5: лендинг — форма заявки и портфолио-лайтбокс
(index.html: handleSend() ~L835, лайтбокс-скрипт ~L856-878).

Тесты запускают index.html в реальном headless Chromium через Playwright —
это не «структурная» проверка HTML, а фактическое исполнение JS в браузере."""
import pathlib

import pytest
from playwright.sync_api import sync_playwright

INDEX_URL = pathlib.Path(__file__).resolve().parent.parent.joinpath("index.html").as_uri()


@pytest.fixture(scope="module")
def page():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        pg = browser.new_page()
        pg.goto(INDEX_URL)
        yield pg
        browser.close()


def test_telegram_contact_links_point_to_correct_accounts(page):
    hrefs = page.eval_on_selector_all("a[href*='t.me']", "els => els.map(e => e.href)")
    assert any("t.me/GolubkaSveta" in h for h in hrefs)
    assert any("t.me/nejroSvetlana" in h for h in hrefs)


def test_portfolio_lightbox_opens_on_click_and_closes_on_escape(page):
    card = page.locator(".portfolio-card").first
    card.click()

    overlay = page.locator("#lightbox")
    assert "active" in (overlay.get_attribute("class") or "")

    img_src = page.locator("#lightbox-img").get_attribute("src")
    assert img_src and img_src.endswith(".png")

    page.keyboard.press("Escape")
    assert "active" not in (overlay.get_attribute("class") or "")


def test_lightbox_closes_on_overlay_click_outside_image(page):
    page.locator(".portfolio-card").first.click()
    overlay = page.locator("#lightbox")
    assert "active" in (overlay.get_attribute("class") or "")

    overlay.click(position={"x": 5, "y": 5})  # клик мимо картинки, по фону
    assert "active" not in (overlay.get_attribute("class") or "")


def test_contact_form_elements_do_not_exist_on_page(page):
    """RED (реальный баг): CSS-классы .f-in/.f-btn и функция handleSend() (index.html:835-848)
    остались от старой версии секции "Написать мне", которая сейчас заменена на одну
    кнопку-ссылку в Telegram (index.html:780-793). Самой формы (`<input class="f-in">`,
    `<button class="f-btn">`) в разметке больше нет ни одной — это неиспользуемый
    мёртвый код, а не рабочая, но "тихая" форма."""
    inputs = page.locator(".f-in")
    buttons = page.locator(".f-btn")
    assert inputs.count() == 0, "ожидалась 0 — .f-in действительно отсутствуют в разметке"
    assert buttons.count() == 0, "ожидалась 0 — .f-btn действительно отсутствуют в разметке"


def test_handle_send_throws_if_ever_invoked(page):
    """RED (реальный баг, продолжение предыдущего теста): поскольку .f-in в DOM нет,
    вызов handleSend() (например, по регрессии кто-то вернёт вызов в разметку) немедленно
    упадёт на `ins[0].value` — `ins[0]` будет undefined. Функция ничего не проверяет
    перед обращением к результатам querySelectorAll."""
    with pytest.raises(Exception):
        page.evaluate("handleSend()")
