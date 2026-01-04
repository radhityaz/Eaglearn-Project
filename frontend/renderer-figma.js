/**
 * EVOLUTIONARY PROTOTYPE - Figma Mode Renderer Script
 * Parity-focused runtime for EXPLORATORY validation.
 * Dynamic behaviours trimmed to preserve layout fidelity with Figma node 1:5.
 */
(() => {
  const parityLog = (message) => console.info('[parity][figma]', message);

  const disableInteractiveElement = (element) => {
    if (!element) {
      return;
    }
    element.disabled = true;
    element.setAttribute('aria-disabled', 'true');
    element.setAttribute('data-static', 'true');
  };

  const freezeActionDeck = () => {
    const actionButtons = document.querySelectorAll('[data-action]');
    if (!actionButtons.length) {
      return;
    }
    actionButtons.forEach(disableInteractiveElement);
    parityLog('action deck frozen (focus/report buttons set to static)');
  };

  const freezeTimelineTabs = () => {
    const tabs = document.querySelectorAll('.timeline-tab');
    if (!tabs.length) {
      return;
    }
    tabs.forEach((tab) => {
      disableInteractiveElement(tab);
      tab.setAttribute('aria-pressed', tab.classList.contains('is-active') ? 'true' : 'false');
    });
    parityLog('timeline tabs disabled to preserve parity capture');
  };

  const markStaticDocumentState = () => {
    document.body.dataset.figmaParity = 'static';
  };

  const initializeFigmaParity = () => {
    markStaticDocumentState();
    freezeActionDeck();
    freezeTimelineTabs();
    parityLog('dynamic timers removed; layout locked for validation');
    console.log('Figma mode static parity initialized');
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeFigmaParity, { once: true });
  } else {
    initializeFigmaParity();
  }
})();
