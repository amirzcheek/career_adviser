// Простой словарь интерфейса на трёх языках: казахский, русский, английский.
// Переключатель языка меняет и подписи интерфейса, и язык ответов модели
// (значение language, уходящее в API).

export const LANGUAGES = [
  { value: "kk", label: "Қазақша" },
  { value: "ru", label: "Русский" },
  { value: "en", label: "English" },
];

export const STRINGS = {
  ru: {
    title: "Карьерный ИИ-консультант",
    portal: "← Вернуться на портал",
    navChat: "Консультация",
    navInterview: "Тренировка собеседования",
    chatIntro:
      "Задайте вопрос о карьере в спорте — отвечу по базе знаний вуза и приведу источники.",
    placeholder: "Напишите вопрос…",
    send: "Отправить",
    typing: "Консультант печатает…",
    sources: "Источники",
    you: "Вы",
    assistant: "Консультант",
    interviewIntro:
      "Выберите профессию и тренируйтесь проходить собеседование. Бот задаёт вопросы и даёт обратную связь.",
    profession: "Профессия",
    startInterview: "Начать собеседование",
    answerPlaceholder: "Ваш ответ…",
    demoBadge: "демо-режим (модель не подключена)",
    errorPrefix: "Ошибка",
    emptyChat: "Здесь появится диалог с консультантом.",
    restart: "Начать заново",
    logout: "Выйти",
    admin: "Админка",
    adminTitle: "Администрирование базы знаний",
    adminDesc:
      "Пересборка поискового индекса после изменения базы знаний или добавления вакансий.",
    adminBadge: "только для админов",
    healthTitle: "Состояние сервиса",
    store: "Хранилище",
    chunks: "Фрагментов в индексе",
    mode: "Режим",
    modeDemo: "демо (модель не подключена)",
    modeLive: "рабочий",
    tokenLabel: "Admin-токен",
    tokenHint: "значение ADMIN_TOKEN сервера",
    rebuild: "Пересобрать индекс",
    rebuilding: "Пересборка…",
    rebuildOk: "Готово. Записано фрагментов:",
    accessDenied: "Доступ только для администраторов.",
  },
  kk: {
    title: "Карьералық ЖИ-кеңесші",
    portal: "← Порталға оралу",
    navChat: "Кеңес алу",
    navInterview: "Сұхбатқа дайындық",
    chatIntro:
      "Спорттағы мансап туралы сұрақ қойыңыз — университет білім қорына сүйеніп жауап беремін.",
    placeholder: "Сұрағыңызды жазыңыз…",
    send: "Жіберу",
    typing: "Кеңесші жазып жатыр…",
    sources: "Дереккөздер",
    you: "Сіз",
    assistant: "Кеңесші",
    interviewIntro:
      "Мамандықты таңдап, сұхбаттан өтуге жаттығыңыз. Бот сұрақ қойып, кері байланыс береді.",
    profession: "Мамандық",
    startInterview: "Сұхбатты бастау",
    answerPlaceholder: "Сіздің жауабыңыз…",
    demoBadge: "демо-режим (модель қосылмаған)",
    errorPrefix: "Қате",
    emptyChat: "Мұнда кеңесшімен сұхбат пайда болады.",
    restart: "Қайта бастау",
    logout: "Шығу",
    admin: "Әкімші панелі",
    adminTitle: "Білім қорын басқару",
    adminDesc:
      "Білім қоры өзгергеннен немесе вакансиялар қосылғаннан кейін іздеу индексін қайта құру.",
    adminBadge: "тек әкімшілерге",
    healthTitle: "Сервис күйі",
    store: "Қойма",
    chunks: "Индекстегі фрагменттер",
    mode: "Режим",
    modeDemo: "демо (модель қосылмаған)",
    modeLive: "жұмыс режимі",
    tokenLabel: "Admin-токен",
    tokenHint: "сервердің ADMIN_TOKEN мәні",
    rebuild: "Индексті қайта құру",
    rebuilding: "Қайта құрылуда…",
    rebuildOk: "Дайын. Жазылған фрагменттер:",
    accessDenied: "Тек әкімшілерге қолжетімді.",
  },
  en: {
    title: "Career AI Advisor",
    portal: "← Back to portal",
    navChat: "Consultation",
    navInterview: "Mock interview",
    chatIntro:
      "Ask about a career in sports — I answer from the university knowledge base and cite sources.",
    placeholder: "Type your question…",
    send: "Send",
    typing: "Advisor is typing…",
    sources: "Sources",
    you: "You",
    assistant: "Advisor",
    interviewIntro:
      "Pick a profession and practise interviews. The bot asks questions and gives feedback.",
    profession: "Profession",
    startInterview: "Start interview",
    answerPlaceholder: "Your answer…",
    demoBadge: "demo mode (model not connected)",
    errorPrefix: "Error",
    emptyChat: "Your conversation with the advisor will appear here.",
    restart: "Restart",
    logout: "Sign out",
    admin: "Admin panel",
    adminTitle: "Knowledge base administration",
    adminDesc:
      "Rebuild the search index after changing the knowledge base or adding vacancies.",
    adminBadge: "admins only",
    healthTitle: "Service status",
    store: "Store",
    chunks: "Chunks in index",
    mode: "Mode",
    modeDemo: "demo (model not connected)",
    modeLive: "live",
    tokenLabel: "Admin token",
    tokenHint: "server ADMIN_TOKEN value",
    rebuild: "Rebuild index",
    rebuilding: "Rebuilding…",
    rebuildOk: "Done. Chunks written:",
    accessDenied: "Administrators only.",
  },
};

// Список профессий для тренировки собеседования (значение уходит в API как есть).
export const PROFESSIONS = [
  "Тренер",
  "Спортивный менеджер",
  "Реабилитолог / физиотерапевт",
  "Учитель физкультуры",
  "Спортивный психолог",
  "Спортивный диетолог",
  "Фитнес-инструктор",
  "Организатор соревнований",
  "Спортивный журналист",
];

export function t(language, key) {
  const dict = STRINGS[language] || STRINGS.ru;
  return dict[key] ?? STRINGS.ru[key] ?? key;
}
