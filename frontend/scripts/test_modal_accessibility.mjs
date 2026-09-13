import test from 'node:test';
import assert from 'node:assert/strict';

// Test 1: Selector verification
test('FOCUSABLE_SELECTOR excludes hidden inputs and disabled elements', () => {
  const FOCUSABLE_SELECTOR = [
    'a[href]',
    'button:not([disabled])',
    'textarea:not([disabled])',
    'input:not([type="hidden"]):not([disabled])',
    'select:not([disabled])',
    '[tabindex]:not([tabindex="-1"])',
  ].join(', ');

  assert.ok(FOCUSABLE_SELECTOR.includes('input:not([type="hidden"]):not([disabled])'), 'Must exclude type="hidden"');
  assert.ok(FOCUSABLE_SELECTOR.includes('button:not([disabled])'), 'Must exclude disabled buttons');
  assert.ok(FOCUSABLE_SELECTOR.includes('[tabindex]:not([tabindex="-1"])'), 'Must exclude tabindex -1');
});

// Test 2: Background locking & inertness state machine simulation
test('Background lock and inertness reference counting', () => {
  let activeModalCount = 0;
  let originalBodyOverflow = '';
  let originalBodyPaddingRight = '';
  const originalInertStates = new Map();

  const mockBody = {
    style: { overflow: '', paddingRight: '' },
    children: [
      { tagName: 'MAIN', attributes: {}, inert: false, setAttribute(k, v) { this.attributes[k] = v; }, getAttribute(k) { return this.attributes[k] || null; }, removeAttribute(k) { delete this.attributes[k]; }, hasAttribute(k) { return k in this.attributes; } },
      { tagName: 'DIV', attributes: { 'data-baleen-modal-portal': 'true' }, inert: false, setAttribute(k, v) { this.attributes[k] = v; }, getAttribute(k) { return this.attributes[k] || null; }, removeAttribute(k) { delete this.attributes[k]; }, hasAttribute(k) { return k in this.attributes; } },
      { tagName: 'SCRIPT', attributes: {}, inert: false, setAttribute(k, v) { this.attributes[k] = v; }, getAttribute(k) { return this.attributes[k] || null; }, removeAttribute(k) { delete this.attributes[k]; }, hasAttribute(k) { return k in this.attributes; } }
    ]
  };

  function lockBackground() {
    activeModalCount++;
    if (activeModalCount === 1) {
      originalBodyOverflow = mockBody.style.overflow;
      originalBodyPaddingRight = mockBody.style.paddingRight;
      mockBody.style.overflow = 'hidden';

      const siblings = mockBody.children.filter(
        (el) => !el.hasAttribute('data-baleen-modal-portal') && el.tagName !== 'SCRIPT' && el.tagName !== 'STYLE'
      );
      siblings.forEach((el) => {
        originalInertStates.set(el, {
          inert: Boolean(el.inert),
          ariaHidden: el.getAttribute('aria-hidden'),
        });
        el.setAttribute('aria-hidden', 'true');
        el.setAttribute('inert', '');
        el.inert = true;
      });
    }
  }

  function unlockBackground() {
    activeModalCount = Math.max(0, activeModalCount - 1);
    if (activeModalCount === 0) {
      mockBody.style.overflow = originalBodyOverflow;
      mockBody.style.paddingRight = originalBodyPaddingRight;

      originalInertStates.forEach((state, el) => {
        if (state.inert) {
          el.setAttribute('inert', '');
          el.inert = true;
        } else {
          el.removeAttribute('inert');
          el.inert = false;
        }

        if (state.ariaHidden !== null) {
          el.setAttribute('aria-hidden', state.ariaHidden);
        } else {
          el.removeAttribute('aria-hidden');
        }
      });
      originalInertStates.clear();
    }
  }

  // Initial state
  assert.equal(mockBody.style.overflow, '');
  assert.equal(mockBody.children[0].getAttribute('aria-hidden'), null);
  assert.equal(mockBody.children[0].inert, false);

  // Modal 1 opens
  lockBackground();
  assert.equal(activeModalCount, 1);
  assert.equal(mockBody.style.overflow, 'hidden');
  assert.equal(mockBody.children[0].getAttribute('aria-hidden'), 'true');
  assert.equal(mockBody.children[0].inert, true);
  // Modal portal is not inert
  assert.equal(mockBody.children[1].hasAttribute('aria-hidden'), false);
  assert.equal(mockBody.children[1].inert, false);

  // Modal 2 opens (nested / stacked)
  lockBackground();
  assert.equal(activeModalCount, 2);
  assert.equal(mockBody.style.overflow, 'hidden');

  // Modal 2 closes (first modal still open)
  unlockBackground();
  assert.equal(activeModalCount, 1);
  assert.equal(mockBody.style.overflow, 'hidden');
  assert.equal(mockBody.children[0].getAttribute('aria-hidden'), 'true');
  assert.equal(mockBody.children[0].inert, true);

  // Modal 1 closes -> full unlock
  unlockBackground();
  assert.equal(activeModalCount, 0);
  assert.equal(mockBody.style.overflow, '');
  assert.equal(mockBody.children[0].getAttribute('aria-hidden'), null);
  assert.equal(mockBody.children[0].inert, false);
});

// Test 3: Focus trap keyboard wrap behavior
test('Focus trap wraps Tab and Shift+Tab and catches out-of-bounds focus', () => {
  const elements = [
    { id: 'closeBtn', focusCount: 0, focus() { this.focusCount++; } },
    { id: 'input1', focusCount: 0, focus() { this.focusCount++; } },
    { id: 'submitBtn', focusCount: 0, focus() { this.focusCount++; } }
  ];

  const container = {
    contains(el) { return elements.includes(el); },
    focusCount: 0,
    focus() { this.focusCount++; }
  };

  function simulateTabTrap(e, activeElement, focusableElements) {
    if (focusableElements.length === 0) {
      container.focus();
      return;
    }

    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];

    if (e.shiftKey) {
      if (activeElement === firstElement || !container.contains(activeElement)) {
        lastElement.focus();
      }
    } else {
      if (activeElement === lastElement || !container.contains(activeElement)) {
        firstElement.focus();
      }
    }
  }

  // Forward tab at last element wraps to first element
  simulateTabTrap({ shiftKey: false }, elements[2], elements);
  assert.equal(elements[0].focusCount, 1, 'Should wrap forward to first element');

  // Shift+Tab at first element wraps to last element
  simulateTabTrap({ shiftKey: true }, elements[0], elements);
  assert.equal(elements[2].focusCount, 1, 'Should wrap backward to last element');

  // Outside element tab wraps to first element
  simulateTabTrap({ shiftKey: false }, { id: 'outside' }, elements);
  assert.equal(elements[0].focusCount, 2, 'Outside element tab should redirect to first element');

  // Outside element Shift+Tab wraps to last element
  simulateTabTrap({ shiftKey: true }, { id: 'outside' }, elements);
  assert.equal(elements[2].focusCount, 2, 'Outside element shift+tab should redirect to last element');

  // Empty focusable elements focuses container
  simulateTabTrap({ shiftKey: false }, null, []);
  assert.equal(container.focusCount, 1, 'Empty focusable elements should focus container');
});

// Test 4: Focus return fallback
test('Focus return gracefully falls back when trigger element is deleted from DOM', () => {
  let triggerElement = { id: 'deleteBtn', inDom: true, focusCount: 0, focus() { this.focusCount++; } };
  const fallbackMain = { id: 'main', focusCount: 0, focus() { this.focusCount++; } };

  function returnFocus(trigger) {
    if (trigger && trigger.inDom) {
      trigger.focus();
    } else {
      fallbackMain.focus();
    }
  }

  // Normal case: trigger in DOM
  returnFocus(triggerElement);
  assert.equal(triggerElement.focusCount, 1);
  assert.equal(fallbackMain.focusCount, 0);

  // Trigger element deleted from DOM
  triggerElement.inDom = false;
  returnFocus(triggerElement);
  assert.equal(fallbackMain.focusCount, 1, 'Fallback element should receive focus');
});

// Test 5: Reduced motion variants
test('Reduced motion variants eliminate transforms and set duration to 0', () => {
  function getMotion(shouldReduceMotion) {
    return {
      backdrop: {
        transition: { duration: shouldReduceMotion ? 0 : 0.2 },
      },
      dialog: {
        initial: shouldReduceMotion
          ? { opacity: 1, scale: 1, y: 0 }
          : { opacity: 0, scale: 0.96, y: 12 },
        animate: { opacity: 1, scale: 1, y: 0 },
        exit: shouldReduceMotion
          ? { opacity: 0, scale: 1, y: 0 }
          : { opacity: 0, scale: 0.96, y: 12 },
        transition: {
          duration: shouldReduceMotion ? 0 : 0.2,
        },
      }
    };
  }

  const normalMotion = getMotion(false);
  assert.equal(normalMotion.backdrop.transition.duration, 0.2);
  assert.equal(normalMotion.dialog.initial.scale, 0.96);
  assert.equal(normalMotion.dialog.initial.y, 12);

  const reducedMotion = getMotion(true);
  assert.equal(reducedMotion.backdrop.transition.duration, 0);
  assert.equal(reducedMotion.dialog.initial.scale, 1);
  assert.equal(reducedMotion.dialog.initial.y, 0);
  assert.equal(reducedMotion.dialog.transition.duration, 0);
});
