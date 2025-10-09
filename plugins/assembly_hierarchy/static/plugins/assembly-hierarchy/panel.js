function translate(i18n, fallback) {
    if (!i18n || typeof i18n._ !== 'function') {
        return fallback;
    }

    return i18n._(fallback);
}

function createTextElement(tag, text, options = {}) {
    const element = document.createElement(tag);
    element.textContent = text;

    Object.assign(element.style, options);

    return element;
}

export function renderHierarchyPanel(target, data) {
    if (!target) {
        console.error('No target element provided for renderHierarchyPanel');
        return;
    }

    // Clear previous content
    while (target.firstChild) {
        target.removeChild(target.firstChild);
    }

    const container = document.createElement('div');
    container.style.display = 'flex';
    container.style.flexDirection = 'column';
    container.style.gap = '0.75rem';

    const heading = createTextElement(
        'h3',
        translate(data?.i18n, 'Assembly hierarchy'),
        {
            margin: '0',
            fontSize: '1.15rem',
            color: 'var(--mantine-color-text, #0f172a)'
        }
    );

    container.appendChild(heading);

    if (!data?.context?.detail_url) {
        const message = createTextElement(
            'p',
            translate(data?.i18n, 'Geen onderdeelcontext beschikbaar voor deze plugin.'),
            {
                margin: '0',
                color: 'var(--mantine-color-dimmed, #475569)'
            }
        );
        container.appendChild(message);
        target.appendChild(container);
        return;
    }

    if (data.context && data.context.part_name) {
        const subtitle = createTextElement(
            'p',
            data.context.part_name,
            {
                margin: '0',
                color: 'var(--mantine-color-dimmed, #475569)',
                fontSize: '0.95rem'
            }
        );
        container.appendChild(subtitle);
    }

    if (data.context && data.context.has_bom === false) {
        const info = createTextElement(
            'p',
            translate(
                data?.i18n,
                'Dit onderdeel heeft nog geen stuklijstregels. De hiërarchie is leeg.'
            ),
            {
                margin: '0',
                padding: '0.75rem 0.85rem',
                borderRadius: '6px',
                background: 'var(--mantine-color-gray-1, #f1f5f9)',
                color: 'var(--mantine-color-dimmed, #475569)'
            }
        );
        container.appendChild(info);
    } else if (data.context && data.context.is_assembly === false) {
        const warn = createTextElement(
            'p',
            translate(
                data?.i18n,
                'Dit onderdeel is niet gemarkeerd als assembly, maar kan wel een stuklijst hebben.'
            ),
            {
                margin: '0',
                padding: '0.75rem 0.85rem',
                borderRadius: '6px',
                border: '1px solid var(--mantine-color-yellow-4, #fbbf24)',
                background: 'var(--mantine-color-yellow-1, #fef3c7)',
                color: 'var(--mantine-color-yellow-9, #92400e)'
            }
        );
        container.appendChild(warn);
    }

    const frameWrapper = document.createElement('div');
    frameWrapper.style.borderRadius = '8px';
    frameWrapper.style.overflow = 'hidden';
    frameWrapper.style.border = '1px solid var(--mantine-color-gray-3, #d1d5db)';

    const detailUrl = new URL(data.context.detail_url, data?.host || window.location.origin);
    detailUrl.searchParams.set('embed', '1');

    const iframe = document.createElement('iframe');
    iframe.src = detailUrl.toString();
    iframe.loading = 'lazy';
    iframe.referrerPolicy = 'same-origin';
    iframe.style.width = '100%';
    iframe.style.minHeight = '520px';
    iframe.style.border = 'none';
    iframe.style.backgroundColor = 'var(--mantine-color-body, #ffffff)';

    frameWrapper.appendChild(iframe);
    container.appendChild(frameWrapper);

    const actions = document.createElement('div');
    actions.style.display = 'flex';
    actions.style.justifyContent = 'flex-end';

    const fullLink = document.createElement('a');
    fullLink.href = new URL(data.context.detail_url, data?.host || window.location.origin).toString();
    fullLink.target = '_blank';
    fullLink.rel = 'noreferrer noopener';
    fullLink.textContent = translate(data?.i18n, 'Open volledige hiërarchie');
    fullLink.style.fontSize = '0.9rem';
    fullLink.style.textDecoration = 'none';
    fullLink.style.fontWeight = '500';
    fullLink.style.color = 'var(--mantine-color-blue-6, #2563eb)';

    actions.appendChild(fullLink);
    container.appendChild(actions);

    target.appendChild(container);
}
