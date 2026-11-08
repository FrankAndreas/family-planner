import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';

// The tab's title names the page ("Settings · Family calendar"), so screen readers and the list of tabs tell the pages
// apart; the calendar is just "Family calendar". Follows the language (accessibility review 2026-11-08)
export function usePageTitle(page: string | null) {
    const { t } = useTranslation();
    const app = t('app.title');
    useEffect(() => {
        document.title = page ? `${page} · ${app}` : app;
    }, [page, app]);
}
