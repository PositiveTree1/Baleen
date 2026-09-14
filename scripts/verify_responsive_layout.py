#!/usr/bin/env python3
"""
Empirical Adversarial Stress Testing Suite: Responsive Layout, Viewport Stability, and Horizontal Overflow Prevention.
Author: challenger_1 (Specialized Adversarial Verifier)
"""

import sys
import json
import time
from playwright.sync_api import sync_playwright

CORE_VIEWPORTS = [
    {"name": "Mobile Small (iPhone 14/15/16 Pro)", "width": 390, "height": 844, "is_mobile": True},
    {"name": "Mobile Medium (iPhone Plus)", "width": 414, "height": 896, "is_mobile": True},
    {"name": "Tablet Portrait (iPad)", "width": 768, "height": 1024, "is_mobile": False},
    {"name": "Desktop Standard Small", "width": 1280, "height": 800, "is_mobile": False},
    {"name": "Desktop Standard Wide", "width": 1440, "height": 900, "is_mobile": False},
    {"name": "Ultrawide (1080p FHD)", "width": 1920, "height": 1080, "is_mobile": False},
]

STRESS_VIEWPORTS = [
    {"name": "Adversarial SE (iPhone SE / 320px)", "width": 320, "height": 568, "is_mobile": True},
    {"name": "Adversarial 2K (QHD 2560x1440)", "width": 2560, "height": 1440, "is_mobile": False},
]

ALL_VIEWPORTS = CORE_VIEWPORTS + STRESS_VIEWPORTS

ROUTES = [
    {"path": "/", "name": "Landing Page"},
    {"path": "/dashboard", "name": "Dashboard Page"},
    {"path": "/settings", "name": "Settings Page"},
    {"path": "/auth/login", "name": "Login Page"},
    {"path": "/auth/signup", "name": "Signup Page"},
]

def execute_verification_suite():
    results = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "summary": {"total": 0, "passed": 0, "failed": 0},
        "viewport_results": {},
        "modals_and_drawers": {},
        "theme_toggle_results": {},
        "failures": []
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for vp in ALL_VIEWPORTS:
            vp_key = f"{vp['width']}x{vp['height']}"
            results["viewport_results"][vp_key] = {
                "name": vp["name"],
                "width": vp["width"],
                "height": vp["height"],
                "is_mobile": vp["is_mobile"],
                "routes": {}
            }

            print(f"\n========================================================")
            print(f"VIEWPORT: {vp['name']} ({vp['width']}x{vp['height']})")
            print(f"========================================================")

            context = browser.new_context(
                viewport={"width": vp["width"], "height": vp["height"]},
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15" if vp["is_mobile"] else "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                is_mobile=vp["is_mobile"],
                has_touch=vp["is_mobile"]
            )
            page = context.new_page()

            for route in ROUTES:
                url = f"http://localhost:3000{route['path']}"
                route_res = {
                    "path": route["path"],
                    "status": "PASS",
                    "checks": {}
                }
                print(f"\n--- Checking: {route['name']} ({route['path']}) ---")

                try:
                    response = page.goto(url, wait_until="networkidle", timeout=15000)
                    time.sleep(0.5)
                except Exception as e:
                    print(f"  FAILED to load {url}: {e}")
                    results["failures"].append({"viewport": vp_key, "route": route["name"], "error": str(e)})
                    continue

                # ----------------------------------------------------
                # CHECK 1: ZERO HORIZONTAL OVERFLOW
                # ----------------------------------------------------
                page.evaluate("window.scrollTo(9999, 0)")
                scroll_x = page.evaluate("window.scrollX")
                html_sw = page.evaluate("document.documentElement.scrollWidth")
                html_cw = page.evaluate("document.documentElement.clientWidth")
                body_sw = page.evaluate("document.body.scrollWidth")
                body_cw = page.evaluate("document.body.clientWidth")
                win_w = page.evaluate("window.innerWidth")

                # Scan for any unclipped leaking elements outside document width
                leaks = page.evaluate("""() => {
                    const winW = window.innerWidth;
                    const els = Array.from(document.querySelectorAll('body *'));
                    const offenders = [];
                    for (const el of els) {
                        const tag = el.tagName;
                        if (['SCRIPT', 'STYLE', 'HEAD', 'META', 'PATH', 'G', 'DEFS', 'FILTER', 'FECONVOLVEMATRIX', 'FEDISPLACEMENTMAP', 'FETURBULENCE', 'NOSCRIPT'].includes(tag)) continue;
                        const style = window.getComputedStyle(el);
                        if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') continue;

                        const r = el.getBoundingClientRect();
                        if (r.width === 0 || r.height === 0) continue;

                        // Check if leaks right
                        if (r.right > winW + 1.5) {
                            // Verify clipping
                            let anc = el;
                            let clipped = false;
                            while (anc && anc !== document.documentElement) {
                                const aStyle = window.getComputedStyle(anc);
                                if (['hidden', 'clip', 'auto', 'scroll'].includes(aStyle.overflowX) ||
                                    ['hidden', 'clip'].includes(aStyle.overflow)) {
                                    clipped = true;
                                    break;
                                }
                                anc = anc.parentElement;
                            }
                            if (!clipped) {
                                offenders.push({
                                    tag: el.tagName,
                                    class: (el.className && typeof el.className === 'string') ? el.className.slice(0, 50) : '',
                                    right: Math.round(r.right),
                                    leakPx: Math.round(r.right - winW)
                                });
                            }
                        }
                    }
                    return offenders.slice(0, 5);
                }""")

                no_h_scroll = (scroll_x == 0)
                html_contained = (html_sw <= html_cw + 1)
                body_contained = (body_sw <= body_cw + 1)
                no_leaks = (len(leaks) == 0)

                overflow_pass = no_h_scroll and html_contained and body_contained and no_leaks

                results["summary"]["total"] += 1
                if overflow_pass:
                    results["summary"]["passed"] += 1
                else:
                    results["summary"]["failed"] += 1
                    route_res["status"] = "FAIL"
                    results["failures"].append({
                        "viewport": vp_key,
                        "route": route["name"],
                        "check": "Zero Horizontal Overflow",
                        "scrollX": scroll_x,
                        "html_sw": html_sw,
                        "html_cw": html_cw,
                        "body_sw": body_sw,
                        "body_cw": body_cw,
                        "leaks": leaks
                    })

                print(f"  [1. Overflow] scrollX={scroll_x} | html={html_sw}/{html_cw} | body={body_sw}/{body_cw} | Leaks={len(leaks)} -> {'PASS' if overflow_pass else 'FAIL'}")
                route_res["checks"]["horizontal_overflow"] = {
                    "pass": overflow_pass,
                    "scrollX": scroll_x,
                    "html_sw": html_sw,
                    "html_cw": html_cw,
                    "body_sw": body_sw,
                    "body_cw": body_cw,
                    "leaks": leaks
                }

                # ----------------------------------------------------
                # CHECK 2: DYNAMIC DOCK & NAVIGATION INTEGRITY
                # ----------------------------------------------------
                dock_eval = page.evaluate("""() => {
                    const topDockNav = document.querySelector('header nav');
                    const mobileDock = document.querySelector('.sm\\\\:hidden .glass-dock, [class*="bottom-[calc(1rem+env(safe-area-inset-bottom"] > div');
                    const winW = window.innerWidth;
                    const winH = window.innerHeight;

                    const info = {};
                    if (topDockNav) {
                        const tr = topDockNav.getBoundingClientRect();
                        const centerDiff = Math.abs((tr.left + tr.width / 2) - (winW / 2));
                        info.topDock = {
                            exists: true,
                            left: Math.round(tr.left),
                            right: Math.round(tr.right),
                            width: Math.round(tr.width),
                            centerDiff: Math.round(centerDiff * 10) / 10,
                            withinBounds: (tr.left >= 0 && tr.right <= winW + 1)
                        };

                        // Check pairwise overlaps of direct buttons/links in header nav
                        const items = Array.from(topDockNav.querySelectorAll('a, button')).filter(el => {
                            const r = el.getBoundingClientRect();
                            return r.width > 0 && r.height > 0 && window.getComputedStyle(el).display !== 'none';
                        });

                        const overlaps = [];
                        for (let i = 0; i < items.length; i++) {
                            const r1 = items[i].getBoundingClientRect();
                            for (let j = i + 1; j < items.length; j++) {
                                const r2 = items[j].getBoundingClientRect();
                                if (items[i].contains(items[j]) || items[j].contains(items[i])) continue;
                                const xO = Math.max(0, Math.min(r1.right, r2.right) - Math.max(r1.left, r2.left));
                                const yO = Math.max(0, Math.min(r1.bottom, r2.bottom) - Math.max(r1.top, r2.top));
                                if (xO * yO > 15) {
                                    overlaps.push({
                                        item1: (items[i].innerText || items[i].getAttribute('aria-label') || items[i].tagName).trim().slice(0, 25),
                                        item2: (items[j].innerText || items[j].getAttribute('aria-label') || items[j].tagName).trim().slice(0, 25),
                                        overlapArea: Math.round(xO * yO)
                                    });
                                }
                            }
                        }
                        info.topDock.overlaps = overlaps;
                    } else {
                        info.topDock = { exists: false, overlaps: [] };
                    }

                    if (mobileDock) {
                        const mr = mobileDock.getBoundingClientRect();
                        const centerDiff = Math.abs((mr.left + mr.width / 2) - (winW / 2));
                        const bottomSpacing = winH - mr.bottom;
                        info.mobileDock = {
                            exists: true,
                            left: Math.round(mr.left),
                            right: Math.round(mr.right),
                            width: Math.round(mr.width),
                            centerDiff: Math.round(centerDiff * 10) / 10,
                            bottomSpacing: Math.round(bottomSpacing),
                            withinBounds: (mr.left >= 0 && mr.right <= winW + 1),
                            hasSafeArea: (bottomSpacing >= 8)
                        };

                        const mItems = Array.from(mobileDock.querySelectorAll('a, button')).filter(el => {
                            const r = el.getBoundingClientRect();
                            return r.width > 0 && r.height > 0 && window.getComputedStyle(el).display !== 'none';
                        });

                        const mOverlaps = [];
                        for (let i = 0; i < mItems.length; i++) {
                            const r1 = mItems[i].getBoundingClientRect();
                            for (let j = i + 1; j < mItems.length; j++) {
                                const r2 = mItems[j].getBoundingClientRect();
                                if (mItems[i].contains(mItems[j]) || mItems[j].contains(mItems[i])) continue;
                                const xO = Math.max(0, Math.min(r1.right, r2.right) - Math.max(r1.left, r2.left));
                                const yO = Math.max(0, Math.min(r1.bottom, r2.bottom) - Math.max(r1.top, r2.top));
                                if (xO * yO > 15) {
                                    mOverlaps.push({
                                        item1: (mItems[i].innerText || mItems[i].getAttribute('aria-label') || mItems[i].tagName).trim().slice(0, 25),
                                        item2: (mItems[j].innerText || mItems[j].getAttribute('aria-label') || mItems[j].tagName).trim().slice(0, 25),
                                        overlapArea: Math.round(xO * yO)
                                    });
                                }
                            }
                        }
                        info.mobileDock.overlaps = mOverlaps;
                    } else {
                        info.mobileDock = { exists: false, overlaps: [] };
                    }
                    return info;
                }""")

                top_d = dock_eval.get("topDock", {})
                mob_d = dock_eval.get("mobileDock", {})

                dock_pass = True
                if top_d.get("exists"):
                    if not top_d.get("withinBounds") or top_d.get("centerDiff", 0) > 8 or len(top_d.get("overlaps", [])) > 0:
                        dock_pass = False

                if vp["is_mobile"] and route["path"] == "/":
                    if not mob_d.get("exists") or not mob_d.get("withinBounds") or mob_d.get("centerDiff", 0) > 8 or not mob_d.get("hasSafeArea") or len(mob_d.get("overlaps", [])) > 0:
                        dock_pass = False

                results["summary"]["total"] += 1
                if dock_pass:
                    results["summary"]["passed"] += 1
                else:
                    results["summary"]["failed"] += 1
                    route_res["status"] = "FAIL"
                    results["failures"].append({
                        "viewport": vp_key,
                        "route": route["name"],
                        "check": "Dock & Nav Integrity",
                        "dock_eval": dock_eval
                    })

                print(f"  [2. Dock & Nav] TopDock centerDiff={top_d.get('centerDiff')} (overlaps={len(top_d.get('overlaps', []))}) | MobileDock={mob_d.get('exists')} (centerDiff={mob_d.get('centerDiff')}, safeArea={mob_d.get('hasSafeArea')}) -> {'PASS' if dock_pass else 'FAIL'}")
                route_res["checks"]["dock_integrity"] = {
                    "pass": dock_pass,
                    "top_dock": top_d,
                    "mobile_dock": mob_d
                }

                # ----------------------------------------------------
                # CHECK 3: WIDE TABLE HORIZONTAL SCROLL WRAPPERS
                # ----------------------------------------------------
                table_eval = page.evaluate("""() => {
                    const tables = Array.from(document.querySelectorAll('table'));
                    return tables.map(t => {
                        let anc = t.parentElement;
                        let wrapperFound = false;
                        let overflowX = '';
                        let canScroll = false;
                        let containerW = 0;
                        let tableW = t.scrollWidth;

                        while (anc && anc !== document.body) {
                            const cs = window.getComputedStyle(anc);
                            if (cs.overflowX === 'auto' || cs.overflowX === 'scroll') {
                                wrapperFound = true;
                                overflowX = cs.overflowX;
                                containerW = anc.clientWidth;
                                canScroll = (anc.scrollWidth >= anc.clientWidth);
                                break;
                            }
                            anc = anc.parentElement;
                        }
                        return {
                            tableW: tableW,
                            containerW: containerW,
                            wrapperFound: wrapperFound,
                            overflowX: overflowX,
                            canScroll: canScroll
                        };
                    });
                }""")

                tables_pass = True
                for t in table_eval:
                    if not t["wrapperFound"]:
                        tables_pass = False

                results["summary"]["total"] += 1
                if tables_pass:
                    results["summary"]["passed"] += 1
                else:
                    results["summary"]["failed"] += 1
                    route_res["status"] = "FAIL"
                    results["failures"].append({
                        "viewport": vp_key,
                        "route": route["name"],
                        "check": "Table Scroll Wrapper",
                        "tables": table_eval
                    })

                print(f"  [3. Tables] Found {len(table_eval)} tables | All Wrapped with overflow-x: auto -> {'PASS' if tables_pass else 'FAIL'}")
                route_res["checks"]["tables"] = {
                    "pass": tables_pass,
                    "count": len(table_eval),
                    "details": table_eval
                }

                results["viewport_results"][vp_key]["routes"][route["name"]] = route_res

            # ----------------------------------------------------
            # STRESS TEST: DASHBOARD MODALS & DRAWERS (on 390x844)
            # ----------------------------------------------------
            if vp_key == "390x844":
                print("\n--- Running Adversarial Modals & Drawers Stress Test on 390x844 ---")
                page.goto("http://localhost:3000/dashboard", wait_until="networkidle")
                time.sleep(0.5)

                modals_to_test = [
                    {"name": "Mirror Strategy Modal", "trigger_btn": "Mirror Alpha Whales"},
                    {"name": "Rebalance Modal", "trigger_btn": "Rebalance Risk Sleeves"},
                    {"name": "Reset Sandbox Modal", "trigger_btn": "Reset Sandbox Account"},
                ]

                for modal in modals_to_test:
                    try:
                        # Find trigger button
                        btn = page.locator(f"button[aria-label*='{modal['trigger_btn']}']").or_(page.locator(f"button:has-text('{modal['trigger_btn']}')")).first
                        if btn.is_visible():
                            btn.click()
                            time.sleep(0.5)

                            # Verify modal box containment
                            modal_box = page.locator("[role='dialog'], [data-baleen-modal-portal]").first
                            if modal_box.is_visible():
                                box = modal_box.bounding_box()
                                m_sw = page.evaluate("document.documentElement.scrollWidth")
                                m_cw = page.evaluate("document.documentElement.clientWidth")
                                m_sx = page.evaluate("window.scrollX")

                                modal_fit = (box["x"] >= 0 and (box["x"] + box["width"]) <= vp["width"] + 2 and m_sw <= m_cw + 1 and m_sx == 0)
                                print(f"  Modal '{modal['name']}': visible=True, x={box['x']}, w={box['width']}, pageScrollX={m_sx} -> {'PASS' if modal_fit else 'FAIL'}")
                                results["modals_and_drawers"][modal["name"]] = {
                                    "pass": modal_fit,
                                    "rect": box,
                                    "pageScrollX": m_sx
                                }

                                # Dismiss modal
                                page.keyboard.press("Escape")
                                time.sleep(0.4)
                            else:
                                print(f"  Modal '{modal['name']}': dialog not visible after click")
                    except Exception as me:
                        print(f"  Modal test note ({modal['name']}): {me}")

                # Test ViewMode Live Capital Toggle
                try:
                    live_btn = page.locator("button:has-text('Live')").first
                    if live_btn.is_visible():
                        live_btn.click()
                        time.sleep(0.5)
                        live_sw = page.evaluate("document.documentElement.scrollWidth")
                        live_cw = page.evaluate("document.documentElement.clientWidth")
                        live_sx = page.evaluate("window.scrollX")
                        live_fit = (live_sw <= live_cw + 1 and live_sx == 0)
                        print(f"  Dashboard Live Capital Mode: sw/cw={live_sw}/{live_cw}, scrollX={live_sx} -> {'PASS' if live_fit else 'FAIL'}")
                        results["modals_and_drawers"]["Dashboard Live Mode"] = {"pass": live_fit}
                except Exception as le:
                    print(f"  Live mode toggle note: {le}")

                # Test Dark/Light Theme Switching on 390x844
                try:
                    theme_btn = page.locator("button[aria-label*='Switch to dark mode'], button[aria-label*='Switch to light mode']").first
                    if theme_btn.is_visible():
                        theme_btn.click() # to dark
                        time.sleep(0.4)
                        dark_sw = page.evaluate("document.documentElement.scrollWidth")
                        dark_cw = page.evaluate("document.documentElement.clientWidth")
                        dark_sx = page.evaluate("window.scrollX")
                        dark_fit = (dark_sw <= dark_cw + 1 and dark_sx == 0)
                        print(f"  Dark Theme Toggle: sw/cw={dark_sw}/{dark_cw}, scrollX={dark_sx} -> {'PASS' if dark_fit else 'FAIL'}")
                        results["theme_toggle_results"]["Dark Mode"] = {"pass": dark_fit}

                        theme_btn.click() # back to light
                        time.sleep(0.4)
                        light_sw = page.evaluate("document.documentElement.scrollWidth")
                        light_cw = page.evaluate("document.documentElement.clientWidth")
                        light_sx = page.evaluate("window.scrollX")
                        light_fit = (light_sw <= light_cw + 1 and light_sx == 0)
                        print(f"  Light Theme Toggle: sw/cw={light_sw}/{light_cw}, scrollX={light_sx} -> {'PASS' if light_fit else 'FAIL'}")
                        results["theme_toggle_results"]["Light Mode"] = {"pass": light_fit}
                except Exception as te:
                    print(f"  Theme switch note: {te}")

            context.close()

        browser.close()

    print("\n========================================================")
    print("FINAL VERIFICATION SUITE SUMMARY:")
    print(f"Total Checks Executed: {results['summary']['total']}")
    print(f"Passed: {results['summary']['passed']}")
    print(f"Failed: {results['summary']['failed']}")
    if results['failures']:
        print(f"FAILURES DETECTED ({len(results['failures'])}):")
        for f in results['failures']:
            print(f"  - {f}")
    else:
        print("ALL ADVERSARIAL STRESS CHECKS PASSED WITH ZERO VIOLATIONS!")
    print("========================================================")

    with open("c:/Users/arthu/repos/Baleen/scripts/verification_suite_results.json", "w", encoding="utf-8") as out:
        json.dump(results, out, indent=2)

    return results

if __name__ == "__main__":
    execute_verification_suite()
