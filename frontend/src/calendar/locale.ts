import { de, enUS } from 'date-fns/locale';
import { useTranslation } from 'react-i18next';

// date-fns texts (weekday and month names) in the page's language
export function useDateLocale() {
    const { i18n } = useTranslation();
    return i18n.language === 'en' ? enUS : de;
}
