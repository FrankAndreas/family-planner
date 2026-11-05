import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import de from './locales/de';
import en from './locales/en';

export type Language = 'de' | 'en';

// The wall has no login: it speaks the planner's default language (/api/config). The settings speak the logged-in
// parent's language from the hub
i18n.use(initReactI18next).init({
    resources: { de: { translation: de }, en: { translation: en } },
    lng: 'de',
    fallbackLng: 'de',
    interpolation: { escapeValue: false },
});
document.documentElement.lang = i18n.language;

export function applyLanguage(lang: Language | null | undefined) {
    const wanted = lang === 'en' ? 'en' : 'de';
    if (i18n.language !== wanted) void i18n.changeLanguage(wanted);
    document.documentElement.lang = wanted;
}

export default i18n;
