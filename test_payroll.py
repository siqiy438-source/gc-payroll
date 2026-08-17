import zipfile
from pathlib import Path
from playwright.sync_api import sync_playwright

HTML = Path(__file__).with_name("index.html").resolve().as_uri()
OUT = Path(__file__).with_name("test-output.docx")


def money(n):
    return f"{n:,.2f}".rstrip("0").rstrip(".")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(HTML)
        page.wait_for_load_state("networkidle")

        assert "女装工资" in page.locator("h1").inner_text()
        assert page.locator("#emptyState").is_visible()

        page.locator("#addStaff").click()
        card = page.locator(".staff-card").first
        card.locator('input[data-k="name"]').fill("小美")
        card.locator('input[data-k="sales"]').fill("75000")
        card.locator('input[data-k="halfShifts"]').fill("2")
        card.locator('input[data-k="halfShifts"]').blur()
        page.wait_for_timeout(200)

        # 75000 * 1% + 4000 + 2*30 = 750 + 4000 + 60 = 4810
        assert "4,810" in card.locator(".sum").inner_text()
        assert "75,000 × 1%" in card.locator(".rows").text_content()

        card.locator('input[data-k="sales"]').fill("90000")
        card.locator('input[data-k="sales"]').blur()
        page.wait_for_timeout(200)
        # 1600 + 300 + 4000 + 60 = 5960
        assert "5,960" in card.locator(".sum").inner_text()
        assert "80,000 × 2%" in card.locator(".rows").text_content()

        card.locator('input[data-k="sales"]').fill("8万")
        card.locator('input[data-k="sales"]').blur()
        page.wait_for_timeout(200)
        # exactly 80000 => 800 + 4000 + 60 = 4860
        assert "4,860" in card.locator(".sum").inner_text()

        page.locator("#addStaff").click()
        page.locator(".staff-card").nth(1).locator('input[data-k="name"]').fill("小芳")
        page.locator(".staff-card").nth(1).locator('input[data-k="sales"]').fill("90000")
        page.locator(".staff-card").nth(1).locator('input[data-k="halfShifts"]').fill("0")
        page.locator(".staff-card").nth(1).locator('input[data-k="halfShifts"]').blur()
        page.wait_for_timeout(200)
        # totals: 4860 + 5900 = 10760
        grand = page.locator("#grandTotal").inner_text()
        assert "10,760" in grand, grand
        assert "CSV" not in page.content()

        # last added employee is selected
        assert page.locator(".staff-card.selected").count() == 1
        assert "小芳" in page.locator("#exportBtn").inner_text()

        with page.expect_download() as download_info:
            page.locator("#exportBtn").click()
        download = download_info.value
        assert "小芳" in download.suggested_filename
        download.save_as(OUT)
        with zipfile.ZipFile(OUT) as zf:
            xml = zf.read("word/document.xml").decode("utf-8")
        assert "小芳" in xml and "小美" not in xml
        assert "¥5,900" in xml and "¥4,860" not in xml
        assert "底薪" in xml and "员工确认" in xml
        assert 'w:type="page"' not in xml

        page.locator(".staff-tab[data-id]").first.click()
        page.wait_for_timeout(700)
        assert "小美" in page.locator("#exportBtn").inner_text()
        with page.expect_download() as download_info:
            page.locator("#exportBtn").click()
        download = download_info.value
        assert "小美" in download.suggested_filename
        download.save_as(OUT)
        with zipfile.ZipFile(OUT) as zf:
            xml = zf.read("word/document.xml").decode("utf-8")
        assert "小美" in xml and "小芳" not in xml
        assert "¥4,860" in xml and "¥5,900" not in xml
        assert "高温补贴" not in xml
        assert "特殊补贴" not in xml

        card = page.locator(".staff-card").first
        card.locator('[data-act="add-sub"]').click()
        card.locator('input[data-k="subName"]').fill("高温补贴")
        card.locator('input[data-k="subAmount"]').fill("200")
        card.locator('input[data-k="subAmount"]').blur()
        page.wait_for_timeout(200)
        assert "5,060" in card.locator(".sum").inner_text()
        assert "高温补贴" in card.locator(".rows").text_content()

        with page.expect_download() as download_info:
            page.locator("#exportBtn").click()
        download = download_info.value
        download.save_as(OUT)
        with zipfile.ZipFile(OUT) as zf:
            xml = zf.read("word/document.xml").decode("utf-8")
        assert "高温补贴" in xml
        assert "¥200" in xml
        assert "¥5,060" in xml
        assert "小芳" not in xml

        card.locator('[data-act="del-sub"]').click()
        page.wait_for_timeout(200)
        assert "4,860" in card.locator(".sum").inner_text()
        assert card.locator('input[data-k="subName"]').count() == 0

        card.locator('[data-act="add-sub"]').click()
        card.locator('input[data-k="subName"]').fill("全勤外补贴")
        card.locator('input[data-k="subAmount"]').fill("100")
        card.locator('input[data-k="subAmount"]').blur()
        page.wait_for_timeout(150)
        card.locator('[data-act="del-last-sub"]').click()
        page.wait_for_timeout(200)
        assert "4,860" in card.locator(".sum").inner_text()
        assert card.locator('input[data-k="subName"]').count() == 0

        page.once("dialog", lambda dialog: dialog.accept())
        page.locator("#clearStaff").click()
        page.wait_for_timeout(200)
        assert page.locator("#emptyState").is_visible()
        assert page.locator(".staff-card").count() == 0
        assert page.locator("#clearStaff").is_disabled()

        page.screenshot(path=str(Path(__file__).with_name("preview-desktop.png")), full_page=True)
        page.set_viewport_size({"width": 390, "height": 844})
        page.screenshot(path=str(Path(__file__).with_name("preview-mobile.png")), full_page=True)
        print("OK")
        browser.close()


if __name__ == "__main__":
    main()
