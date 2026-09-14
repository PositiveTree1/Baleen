from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 390, "height": 844})
    response = page.goto("http://localhost:3000", wait_until="networkidle", timeout=15000)
    print("Status:", response.status if response else "No response")
    title = page.title()
    print("Title:", title)
    
    html_scroll_width = page.evaluate("document.documentElement.scrollWidth")
    html_client_width = page.evaluate("document.documentElement.clientWidth")
    body_scroll_width = page.evaluate("document.body.scrollWidth")
    body_client_width = page.evaluate("document.body.clientWidth")
    print(f"HTML: scrollWidth={html_scroll_width}, clientWidth={html_client_width}")
    print(f"BODY: scrollWidth={body_scroll_width}, clientWidth={body_client_width}")
    
    browser.close()
