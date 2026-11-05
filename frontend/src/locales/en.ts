import type de from './de';

const en: typeof de = {
    app: { title: 'Family calendar' },
    calendar: {
        week: 'Week {{n}}',
        today: 'Today',
        tomorrow: 'Tomorrow',
        allDay: 'all day',
        nothing: 'Nothing planned',
        back: 'Back',
        forward: 'Forward',
        settings: 'Settings',
        close: 'Close',
        problem: 'A calendar can\'t be updated right now',
        views: { day: 'Day', '3day': '3 days', week: 'Week', month: 'Month', agenda: 'Agenda' },
    },
    errors: {
        generic: 'Something went wrong.',
        network: 'The calendar can\'t be reached right now.',
    },
};

export default en;
