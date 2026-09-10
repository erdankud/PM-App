// СГЕНЕРИРОВАНО. Не редактируйте здесь.
//
// Источник — `ios/PMThinkingCoach/Core/Localization/Strings.swift`, пересборка:
//     python3 web/tools/port_strings.py
//
// Обе копии интерфейса живут в одном файле именно затем, чтобы перевод нельзя было
// поправить на одной платформе и забыть на другой.

import { t, plural, capitalize } from "./l10n.js";

export const S = {
Common: {
  get back() { return t("Back", "Назад"); },
  get next() { return t("Next", "Далее"); },
  get continueAction() { return t("Continue", "Продолжить"); },
  get done() { return t("Done", "Готово"); },
  get close() { return t("Close", "Закрыть"); },
  get cancel() { return t("Cancel", "Отмена"); },
  get tryAgain() { return t("Try again", "Повторить"); },
  get loading() { return t("Loading…", "Загрузка…"); },
  get couldntLoad() { return t("Couldn't load", "Не удалось загрузить"); },
  get tagline() { return t("skill map of the craft", "карта навыков профессии"); },
  get skipToContent() { return t("Skip to content", "К содержанию"); },
  get expandMenu() { return t("Expand menu", "Развернуть меню"); },
  get collapseMenu() { return t("Collapse menu", "Свернуть меню"); },
  minutes(count) {
    return t(`${count} min`, `${count} мин`)
  },
  xp(count) {
    return `${count} XP`
  },
  scoreOutOf100(score) {
    return `${score}/100`
  },
  dayStreak(count) {
    return t(
    `${count} day streak`,
    `${count} ${plural(count, "день", "дня", "дней")} подряд`
    )
  },
},
Tab: {
  get learn() { return t("Learn", "Обучение"); },
  get tree() { return t("Skills Map", "Карта навыков"); },
  get practice() { return t("Practice", "Практика"); },
  get progress() { return t("Progress", "Прогресс"); },
  get profile() { return t("Profile", "Профиль"); },
},
Welcome: {
  get headline() { return t( "Practice thinking like a Product Manager", "Тренируйте мышление продакт-менеджера" ); },
  get continueWithApple() { return t("Continue with Apple", "Продолжить с Apple"); },
  get developerSignIn() { return t("Continue without Apple (development)", "Продолжить без Apple (для разработки)"); },
  get privacyNotice() { return t("Privacy notice", "О приватности"); },
},
Auth: {
  get signIn() { return t("Sign in", "Вход"); },
  get signUp() { return t("Create account", "Регистрация"); },
  get email() { return t("Email", "Почта"); },
  get password() { return t("Password", "Пароль"); },
  get emailPlaceholder() { return t("you@example.com", "you@example.com"); },
  get continueWithGoogle() { return t("Continue with Google", "Продолжить с Google"); },
  get or() { return t("or", "или"); },
  get haveAccount() { return t("Already have an account? Sign in", "Уже есть аккаунт? Войти"); },
  get needAccount() { return t("No account yet? Create one", "Нет аккаунта? Создать"); },
  passwordRule(minimum) {
    return t(
    `At least ${minimum} characters.`,
    `Не меньше ${minimum} символов.`
    )
  },
  get invalidCredentials() { return t( "That email and password don't match an account.", "Такая пара почты и пароля не подходит." ); },
  get emailTaken() { return t( "That email already has an account. Sign in instead.", "На эту почту уже есть аккаунт. Войдите." ); },
  get emailInvalid() { return t("That doesn't look like an email address.", "Это не похоже на адрес почты."); },
  get googleUnavailable() { return t( "Google sign-in isn't set up on this server yet.", "Вход через Google на этом сервере пока не настроен." ); },
  get noMethods() { return t( "This server has no sign-in method enabled.", "На этом сервере не включён ни один способ входа." ); },
},
Privacy: {
  get title() { return t("Privacy", "Приватность"); },
  get heading() { return t("What we collect and why", "Что мы собираем и зачем"); },
  get accountTitle() { return t("Your account", "Ваш аккаунт"); },
  get accountBody() { return t( "Signing in with Apple gives us a stable identifier for your account. We do " + "not ask for your name, email, employer, or any demographic information.", "Вход через Apple даёт нам постоянный идентификатор аккаунта. Мы не спрашиваем " + "ваше имя, почту, работодателя и любые демографические данные." ); },
  get writingTitle() { return t("What you write", "То, что вы пишете"); },
  get writingBody() { return t( "The reasoning you write for each challenge is sent to our server and to our " + "AI provider for the sole purpose of generating your feedback. It is " + "never sent to analytics, crash reporting, or notifications.", "Ваша аргументация по каждому заданию отправляется на наш сервер и AI-провайдеру " + "исключительно для подготовки разбора. Она никогда не попадает в аналитику, " + "отчёты об ошибках или уведомления." ); },
  get analyticsTitle() { return t("Product analytics", "Продуктовая аналитика"); },
  get analyticsBody() { return t( "We record which screens you reach and which options you select so we can " + "improve the product. These events never include what you wrote or the " + "feedback you received.", "Мы фиксируем, до каких экранов вы дошли и какие варианты выбрали, чтобы " + "улучшать продукт. В этих событиях никогда нет ни ваших текстов, ни " + "полученного разбора." ); },
  get deletionTitle() { return t("Deleting your account", "Удаление аккаунта"); },
  get deletionBody() { return t( "You can delete your account from Profile at any time. This removes your " + "written responses, your feedback, and your identity link.", "Аккаунт можно удалить в Профиле в любой момент. Вместе с ним удаляются ваши " + "ответы, разборы и связь с вашей учётной записью." ); },
  get scoresTitle() { return t("What scores mean", "Что означают оценки"); },
  get scoresBody() { return t( "Skill scores are practice signals based on your in-app work. They are not an " + "assessment of job readiness and they do not predict hiring outcomes.", "Оценки навыков — это сигналы о вашей практике в приложении. Это не оценка " + "готовности к работе и не прогноз результатов найма." ); },
},
Tree: {
  get loading() { return t("Loading the map…", "Загружаем карту…"); },
  get loadFailed() { return t("Couldn't load the map", "Не удалось загрузить карту"); },
  get continueHere() { return t("Continue here", "Продолжить здесь"); },
  get openBlock() { return t("Open block", "Открыть блок"); },
  get tiersTitle() { return t("Three levels", "Три уровня"); },
  get tiersSubtitle() { return t( "The level is how much uncertainty the task carries, not how hard it is.", "Уровень — это степень неопределённости задачи, а не её сложность." ); },
  get domainsTitle() { return t("Six domains", "Шесть доменов"); },
  get domainsSubtitle() { return t( "Everything is visible from day one. Only the route is earned.", "Всё видно с первого дня. Зарабатывается только маршрут." ); },
  get comingSoon() { return t( "The lessons for this block are still being written.", "Уроки этого блока ещё пишутся." ); },
  get lessonsComingSoon() { return t("Lesson coming soon", "Урок скоро появится"); },
  get currentDirection() { return t("Now studying", "Сейчас изучаете"); },
  get continueLesson() { return t("Continue", "Продолжить"); },
  get blockLessonsTitle() { return t("Lessons of this block", "Уроки этого блока"); },
  get gateLocked() { return t("Opens after the lessons", "Откроется после уроков"); },
  get noDirectionYet() { return t("Nothing started here yet", "Здесь вы ещё не начинали"); },
  blocksProgress(passed, total) {
    return t(`${passed} of ${total} blocks`, `${passed} из ${total} блоков`)
  },
  get blockGoalTitle() { return t("What this block gives you", "Что даёт этот блок"); },
  get blockGoalSubtitle() { return t( "Each question below is one skill. The gate at the end asks you to use them, not to recall them.", "Каждый вопрос ниже — один навык. Гейт в конце просит их применить, а не вспомнить." ); },
  get lessonsTitle() { return t("Lessons", "Уроки"); },
  get startNode() { return t("Start", "Начало"); },
  plateNumber(number) {
    return t(`Plate ${number}`, `Табл. ${number}`)
  },
  skillsLearned(total) {
    return t(`of ${total} learned`, `из ${total} освоено`)
  },
  get zoomIn() { return t("Zoom in", "Приблизить"); },
  get zoomOut() { return t("Zoom out", "Отдалить"); },
  get zoomReset() { return t("Fit the map", "Вся карта"); },
  get openLesson() { return t("Open lesson", "Открыть урок"); },
  get mapHint() { return t( "Drag to move, scroll to zoom. A card is one skill — open it to read its lesson.", "Тяните, чтобы двигать, колесо — масштаб. Карточка — один навык, в ней урок." ); },
  lessonsInNode(count) {
    return t(
    `${count} lessons`,
    `${count} ${plural(count, "урок", "урока", "уроков")}`
    )
  },
  get legendLesson() { return t("Lesson", "Урок"); },
  get legendLessonDone() { return t("Lesson done", "Урок пройден"); },
  get legendGate() { return t("Block gate", "Гейт блока"); },
  get gateTitle() { return t("Gate", "Гейт"); },
  get gateHeadline() { return t("One situation, not a test", "Одна ситуация вместо теста"); },
  get gatePitch() { return t( "A real situation with incomplete data. You make the call and argue it in writing.", "Настоящая ситуация с неполными данными. Вы принимаете решение и обосновываете его письменно." ); },
  get gateNoPenalty() { return t( "Failing costs nothing: no XP is taken away and nothing closes.", "Провал ничего не стоит: XP не отнимается и ничего не закрывается." ); },
  blockSummary(nodes, lessons, minutes) {
    return t(
    `${nodes} skills · ${lessons} lessons · about ${minutes} min`,
    `${nodes} ${plural(nodes, "навык", "навыка", "навыков")} · `
    + `${lessons} ${plural(lessons, "урок", "урока", "уроков")} · около ${minutes} мин`
    )
  },
  lessonNumber(index) {
    return t(`Lesson ${index}`, `Урок ${index}`)
  },
  get takeGate() { return t("Take the gate", "Сдать гейт"); },
  get retakeGate() { return t("Take it again", "Пересдать"); },
  gateSubtitle(threshold) {
    return t(
    `A situation with incomplete data, not a test. ${threshold} out of 100 to pass.`,
    `Ситуация с неполными данными, а не тест. Для зачёта нужно ${threshold} из 100.`
    )
  },
  gateBlockedReason(reason, remaining) {
    switch (reason) {
    case "locked":
    return t(
    "Pass the previous block to open this one.",
    "Сдайте предыдущий блок, чтобы открыть этот."
    )
    case "coming_soon":
    return S.Tree.comingSoon
    case "lessons_remaining":
    return t(
    `${remaining} more ${remaining == 1 ? "lesson" : "lessons"} to finish first.`,
    `Осталось пройти ${remaining} ${plural(remaining, "урок", "урока", "уроков")}.`
    )
    default:
    return t("Not available yet.", "Пока недоступно.")
    }
  },
  lockedExplanation(prerequisites) {
    const list = prerequisites.join(", ")
    return t(
    `Opens once you pass ${list}.`,
    `Откроется, когда вы сдадите ${list}.`
    )
  },
  lessonsProgress(done, total) {
    return t(
    `${done} of ${total} lessons read`,
    `Пройдено ${done} из ${total} ${plural(total, "урока", "уроков", "уроков")}`
    )
  },
  ofBlocks(total) {
    return t(`of ${total}`, `из ${total}`)
  },
  passedOfTotal(passed, total) {
    return t(
    `${passed} of ${total} blocks passed`,
    `Сдано ${passed} из ${total} ${plural(total, "блока", "блоков", "блоков")}`
    )
  },
  tierName(tier) {
    return `Level ${tier}`
  },
  tierSubtitle(tier) {
    switch (tier) {
    case 1:
    return t(
    "One atomic task: gather or produce one concrete thing.",
    "Атомарная задача: собрать или сделать что-то одно."
    )
    case 2:
    return t(
    "Analysis and aggregation: reasoned conclusions from messy input.",
    "Анализ и агрегация: обоснованные выводы из неаккуратных данных."
    )
    default:
    return t(
    "Goals, processes and strategy across a product or a portfolio.",
    "Цели, процессы и стратегия на уровне продукта или портфеля."
    )
    }
  },
  statusLabel(status) {
    switch (status) {
    case "locked": return t("Locked", "Закрыт")
    case "available": return t("Open", "Открыт")
    case "in_progress": return t("In progress", "В процессе")
    case "gate_ready": return t("Ready for the gate", "Готов к гейту")
    case "passed": return t("Passed", "Сдан")
    }
  },
  statusSymbol(status) {
    switch (status) {
    case "locked": return "lock.fill"
    case "available": return "circle"
    case "in_progress": return "circle.lefthalf.filled"
    case "gate_ready": return "flag.fill"
    case "passed": return "checkmark.circle.fill"
    }
  },
},
Lesson: {
  get takeaway() { return t("The point", "Главное"); },
  get checkYourself() { return t("Check yourself", "Проверьте себя"); },
  get checkNotScored() { return t( "Not scored — the gate is where application is checked.", "Не оценивается: применение проверяет гейт." ); },
  get example() { return t("Example", "Пример"); },
  get terms() { return t("Terms in this lesson", "Термины урока"); },
  get exercise() { return t("Exercise", "Упражнение"); },
  get markRead() { return t("Mark as read", "Отметить как прочитанное"); },
  get audioTitle() { return t("Audio overview", "Аудиообзор"); },
  get audioSubtitle() { return t("Two hosts discuss this lesson", "Двое обсуждают этот урок"); },
  get audioLoading() { return t("Preparing…", "Готовлю…"); },
  get audioFailed() { return t("Could not load. Tap to retry.", "Не удалось загрузить. Нажмите ещё раз."); },
  get audioPlay() { return t("Play", "Слушать"); },
  get audioPause() { return t("Pause", "Пауза"); },
  get audioBack15() { return t("Back 15 seconds", "Назад на 15 секунд"); },
  get audioForward15() { return t("Forward 15 seconds", "Вперёд на 15 секунд"); },
  get audioSpeed() { return t("Speed", "Скорость"); },
  get audioPosition() { return t("Position", "Позиция"); },
  get audioBuild() { return t("Generate overview", "Сгенерировать обзор"); },
  get audioBuilding() { return t("Writing and voicing… about a minute", "Пишу и озвучиваю… около минуты"); },
  get audioBuildFailed() { return t("Generation failed. Tap to retry.", "Не получилось. Нажмите, чтобы повторить."); },
  get nextLesson() { return t("Next lesson", "Следующий урок"); },
  get backToBlock() { return t("Back to the block", "Вернуться к блоку"); },
},
Glossary: {
  get title() { return t("Glossary", "Глоссарий"); },
  get searchPrompt() { return t("Search in Russian or English", "Поиск по-русски или по-английски"); },
  get empty() { return t("Nothing found", "Ничего не нашлось"); },
  get seen() { return t("Seen in a lesson", "Встречали в уроке"); },
  get openLesson() { return t("Read the lesson", "Открыть урок"); },
},
Exercise: {
  get title() { return t("Exercise", "Упражнение"); },
  get check() { return t("Check", "Проверить"); },
  get showReference() { return t("Skip and see the reasoning", "Пропустить и посмотреть разбор"); },
  get reference() { return t("How to think about it", "Как рассуждать"); },
  get understood() { return t("Got it", "Понятно"); },
  get orderRight() { return t("Order of magnitude is right", "Порядок верный"); },
  get orderOff() { return t("Order of magnitude differs", "Порядок отличается"); },
  get sameAsReference() { return t("Same as the reasoning", "Как в разборе"); },
  get otherThanReference() { return t("Differs from the reasoning", "Иначе, чем в разборе"); },
  get notAnswered() { return t("Not answered", "Без ответа"); },
  get chooseAnswer() { return t("Choose", "Выберите"); },
},
Learn: {
  get learnMore() { return t("Learn more", "Подробнее"); },
  get blocksTitle() { return t("Blocks of this direction", "Блоки направления"); },
  intro(kind) {
    return kind == "system_design"
    ? t(
    "Six areas of how a product works inside. A product manager does not build them, but every one of them sets a limit on what can be promised and how fast.",
    "Шесть областей того, как продукт устроен внутри. Продакт их не строит, но каждая ставит границу тому, что можно пообещать и как быстро."
    )
    : t(
    "Six directions are not chapters of a course. They are the competencies a product manager is made of: each owns its part of the work, and together they cover the way from research to money.",
    "Шесть направлений — это не разделы курса, а составляющие компетенции продакта: каждое отвечает за свой кусок работы, и вместе они покрывают путь от исследования до денег."
    )
  },
  aboutTitle(kind) {
    return kind == "system_design"
    ? t("How the systems map works", "Как устроена карта систем")
    : t("How the skill map works", "Как устроена карта навыков")
  },
  aboutLead(kind) {
    return kind == "system_design"
    ? t(
    "The job here is not to design systems but to understand the price of a decision: what a promise costs, what it takes to change, and what breaks under load. Six areas, three levels of uncertainty — the same grammar as the product map.",
    "Задача здесь не проектировать системы, а понимать цену решения: сколько стоит обещание, чего стоит его изменить и что ломается под нагрузкой. Шесть областей, три уровня неопределённости — та же грамматика, что и у карты продукта."
    )
    : t(
    "A product manager's job is to get the most value to people with the least time to market. That work does not split into one skill — it splits into six directions, and inside each one the skills differ by how much uncertainty you carry.",
    "Работа продакта — довести до людей максимум ценности за минимум времени до рынка. Эта работа не сводится к одному навыку: она делится на шесть направлений, а внутри каждого навыки отличаются тем, сколько неопределённости вы несёте."
    )
  },
  levelAudience(tier) {
    switch (tier) {
    case 1: return t("Junior level · a single task or feature", "Junior · одиночная задача или фича")
    case 2: return t("Middle and senior level · a project or a product vertical", "Middle и senior · проект или вертикаль продукта")
    default: return t("Senior, head of product, CPO · a product or a portfolio", "Senior, head of product, CPO · продукт или портфель")
    }
  },
  domainBlurb(key) {
    switch (key) {
    case "discovery":
    return t(
    "Qualitative and quantitative research: the user's context, and the problem behind the request.",
    "Качественные и количественные исследования: контекст пользователя и задача, стоящая за просьбой."
    )
    case "value_design":
    return t(
    "Turning findings into a value proposition and then into a concrete solution.",
    "Превращение находок в ценностное предложение, а затем в конкретное решение."
    )
    case "delivery":
    return t(
    "Running the development of that solution and getting it into users' hands.",
    "Управление разработкой решения и доведение его до пользователей."
    )
    case "marketing":
    return t(
    "Acquiring and keeping people, and carrying the product's value to them.",
    "Привлечение и удержание людей и донесение до них ценности продукта."
    )
    case "growth":
    return t(
    "Growing a product that already works, through hypotheses you can actually check.",
    "Развитие уже работающего продукта через гипотезы, которые можно проверить."
    )
    case "economics":
    return t(
    "Turning value into money, and planning the finances that keep it running.",
    "Превращение ценности в деньги и финансовое планирование, на котором всё держится."
    )
    case "data":
    return t(
    "Where the product's data lives, and what makes it expensive to change.",
    "Где живут данные продукта и что делает их изменение дорогим."
    )
    case "integration":
    return t(
    "How the parts of a system agree with each other, and why they come apart.",
    "Как части системы договариваются друг с другом и почему расходятся."
    )
    case "scale":
    return t(
    "What happens when there are a hundred times more users than today.",
    "Что происходит, когда пользователей становится в сто раз больше."
    )
    case "performance":
    return t(
    "What a second of waiting costs, and what a single request costs.",
    "Сколько стоит секунда ожидания и сколько стоит один запрос."
    )
    case "ai_systems":
    return t(
    "What an AI feature is made of, and why it gets expensive faster than it grows.",
    "Из чего состоит AI-фича и почему она дорожает быстрее, чем растёт."
    )
    case "security":
    return t(
    "Who sees what, and what you are obliged to be able to delete.",
    "Кто что видит и что вы обязаны уметь удалить."
    )
    default:
    return ""
    }
  },
  sourceNote(kind) {
    return kind == "system_design"
    ? t(
    "The systems map extends the product one and follows its grammar.",
    "Карта систем расширяет продуктовую и следует её грамматике."
    )
    : t(
    "Six directions, three levels: one grammar for the whole profession.",
    "Шесть направлений и три уровня — одна грамматика на всю профессию."
    )
  },
},
Trees: {
  get product() { return t("Product", "Продукт"); },
  get systems() { return t("Systems", "Системы"); },
  get recommendation() { return t( "New to product? Start with Discovery in the product map.", "Если вы новичок — начните с первого блока карты продукта." ); },
},
Roles: {
  keys: [ "product_manager", "product_analyst", "growth_manager", "scrum_product_owner", "head_of_product", "product_marketing_manager", "product_designer", "project_manager", "cpo", "cmo", ],
  get none() { return t("Not chosen", "Не выбрана"); },
  title(key) {
    switch (key) {
    case "product_manager": return t("Product Manager", "Продакт-менеджер")
    case "product_analyst": return t("Product Analyst", "Продуктовый аналитик")
    case "growth_manager": return t("Growth Manager", "Growth-менеджер")
    case "scrum_product_owner": return t("Scrum Product Owner", "Scrum Product Owner")
    case "head_of_product": return t("Head of Product", "Head of Product")
    case "product_marketing_manager":
    return t("Product Marketing Manager", "Продуктовый маркетолог")
    case "product_designer": return t("Product Designer", "Продуктовый дизайнер")
    case "project_manager": return t("Project Manager", "Проектный менеджер")
    case "cpo": return t("CPO", "CPO")
    case "cmo": return t("CMO", "CMO")
    default: return S.Roles.none
    }
  },
},
Onboarding: {
  get setUpTitle() { return t("Getting started", "Начало"); },
  get howItWorksTitle() { return t("A route, not a library", "Маршрут, а не библиотека"); },
  get howItWorksSubtitle() { return t( "The map of the profession, turned into a path you can walk from zero. " + "Five things worth knowing before the first lesson.", "Карта профессии, превращённая в путь, который можно пройти с нуля. " + "Пять вещей, которые стоит знать до первого урока." ); },
  get stepMapTitle() { return t("Two maps, both open", "Две карты, обе открыты"); },
  get stepMapBody() { return t( "The product map (71 skills) and System Design (96) share one grammar " + "and one switch at the top. Everything is open from day one: start " + "at the first block of the product map if you are new, or anywhere else.", "Карта продукта (71 навык) и System Design (96) устроены одинаково и " + "переключаются наверху экрана. Всё открыто с первого дня: если вы " + "новичок, начните с первого блока карты продукта, но можно и с любого места." ); },
  get stepRingsTitle() { return t("Rings are uncertainty, not seniority", "Кольца показывают неопределённость, а не грейд"); },
  get stepRingsBody() { return t( "The inner ring is a task someone already framed for you. The outer one is " + "where you choose the frame. It says nothing about how good a manager " + "you are.", "Во внутреннем кольце задачу уже поставили за вас. Во внешнем рамку " + "выбираете вы. К оценке вас как менеджера это отношения не имеет." ); },
  get stepLessonsTitle() { return t("Short lessons", "Короткие уроки"); },
  get stepLessonsBody() { return t( "One idea, one model, and where it stops working: three to five minutes on " + "the product map, twelve to fifteen in System Design. Some carry an " + "audio overview: two hosts talking the lesson through, not reading it " + "aloud.", "Одна идея, одна модель и границы, за которыми она не работает: три-пять " + "минут на карте продукта, двенадцать-пятнадцать в System Design. У части " + "уроков есть аудиообзор: двое ведущих обсуждают материал, а не читают " + "его вслух." ); },
  get stepGateTitle() { return t("A gate, not a quiz", "Гейт, а не тест"); },
  get stepGateBody() { return t( "Each block ends in a real situation with incomplete data. You decide and " + "defend the decision in writing. The reasoning is most of the score, " + "so no option is «the right answer» on its own.", "Каждый блок заканчивается настоящей ситуацией с неполными данными. Вы " + "принимаете решение и обосновываете его письменно. Аргументация даёт " + "большую часть баллов, поэтому «правильного варианта» самого по себе тут нет." ); },
  get stepUnlockTitle() { return t("Failing costs nothing", "Несданный гейт ничего не стоит"); },
  get stepUnlockBody() { return t( "No XP is taken away and nothing locks. A failed gate sends you back to the " + "exact lessons that would have helped, and you can retake it. The " + "second sitting is a different situation, so it cannot be passed from " + "memory.", "XP не отнимается и ничего не закрывается. Несданный гейт возвращает вас к " + "конкретным урокам, которых не хватило, и его можно пересдать. Во " + "второй раз ситуация другая, поэтому пройти его по памяти нельзя." ); },
  get roleTitle() { return t("Aiming at a role?", "Метите в конкретную роль?"); },
  get startLearning() { return t("Start learning", "Начать учиться"); },
  get skipRole() { return t("Skip for now", "Пропустить"); },
},
Challenge: {
  Step: {
    get situation() { return t("The situation", "Ситуация"); },
    get investigate() { return t("Investigate", "Разобраться"); },
    get decide() { return t("Decide & defend", "Решить и обосновать"); },
    get consequence() { return t("What happens next", "Что происходит дальше"); },
    get feedback() { return t("Coaching", "Разбор"); },
  },
  get loadingScenario() { return t("Loading the scenario…", "Загружаем сценарий…"); },
  stepProgress(current, total) {
    return t(`Step ${current} of ${total}`, `Шаг ${current} из ${total}`)
  },
  get leaveTitle() { return t("Leave this challenge?", "Выйти из задания?"); },
  get saveAndLeave() { return t("Save and leave", "Сохранить и выйти"); },
  get keepWorking() { return t("Keep working", "Продолжить работу"); },
  get leaveMessage() { return t( "Your work is saved. You can pick it up from Today.", "Работа сохранена. Вернуться к ней можно из вкладки «Сегодня»." ); },
  get yourRole() { return t("Your role", "Ваша роль"); },
  get theCompany() { return t("The company", "Компания"); },
  get whatsHappening() { return t("What's happening", "Что происходит"); },
  get theObjective() { return t("The objective", "Цель"); },
  get constraints() { return t("Constraints", "Ограничения"); },
  get yourTask() { return t("Your task", "Ваша задача"); },
  get whatGoodLooksLike() { return t("What good looks like", "Как выглядит хороший ответ"); },
  get investigatePrompt() { return t("What do you want to look at?", "На что хотите посмотреть?"); },
  evidenceCounter(reviewed, total) {
    return t(
    `${reviewed} of ${total} signals reviewed`,
    `Изучено ${reviewed} из ${total} ${plural(total, "сигнала", "сигналов", "сигналов")}`
    )
  },
  get partialEvidenceNotice() { return t( "This is everything you get. Real decisions are made on partial evidence — say " + "what you can't know as well as what you can.", "Это все данные, что у вас есть. Настоящие решения принимаются на неполных " + "данных — скажите и о том, чего знать нельзя, а не только о том, что знаете." ); },
  get openOneSignal() { return t( "Open at least one signal before deciding.", "Откройте хотя бы один сигнал, прежде чем решать." ); },
  get makeADecision() { return t("Make a decision", "Принять решение"); },
  get reviewed() { return t("Reviewed", "Изучено"); },
  get opensSignal() { return t("Opens this signal", "Открывает этот сигнал"); },
  get collapsesSignal() { return t("Collapses this signal", "Сворачивает этот сигнал"); },
  get severalAnswers() { return t( "Several answers can be defended. What matters is the reasoning.", "Обосновать можно несколько вариантов. Важна именно аргументация." ); },
  get defendYourDecision() { return t("Defend your decision", "Обоснуйте своё решение"); },
  get rationalePlaceholder() { return t( "What evidence, trade-off, and risk informed your choice?", "Какие данные, компромиссы и риски привели вас к этому выбору?" ); },
  get yourReasoning() { return t("Your reasoning", "Ваша аргументация"); },
  get longEnough() { return t("Long enough", "Достаточно длинно"); },
  get saved() { return t("Saved", "Сохранено"); },
  get offlineDraft() { return t( "Saved on this device. It will sync when you're back online — you can't submit " + "until it does.", "Сохранено на этом устройстве. Синхронизируется, когда вы вернётесь в сеть — " + "до этого отправить нельзя." ); },
  get reasoningNotOptionNote() { return t( "Feedback assesses your reasoning, not only which option you picked.", "Разбор оценивает вашу аргументацию, а не только выбранный вариант." ); },
  get submitDecision() { return t("Submit decision", "Отправить решение"); },
  charactersToGo(count) {
    return t(
    `${count} more characters to go.`,
    `Осталось ${count} ${plural(count, "символ", "символа", "символов")}.`
    )
  },
  charactersOver(count) {
    return t(
    `${count} characters over the limit.`,
    `${count} ${plural(count, "символ", "символа", "символов")} сверх лимита.`
    )
  },
  get youChose() { return t("You chose", "Вы выбрали"); },
  get whatHappensNext() { return t("What happens next", "Что происходит дальше"); },
  get whatHappenedNext() { return t("What happened next", "Что произошло дальше"); },
  get loadingOutcome() { return t("Loading the outcome…", "Загружаем исход…"); },
  get seeCoaching() { return t("See coaching", "Посмотреть разбор"); },
  get retryCoaching() { return t("Retry coaching", "Повторить разбор"); },
  get preparingCoaching() { return t("Preparing coaching…", "Готовим разбор…"); },
  get checkAgain() { return t("Check again", "Проверить снова"); },
  get coachingReady() { return t("Your coaching is ready.", "Ваш разбор готов."); },
  get coachingPending() { return t( "Coaching is taking a moment. Your answer is saved — you can leave and come " + "back to it from Today.", "Разбор занимает чуть больше времени. Ответ сохранён — можно выйти и вернуться " + "к нему из вкладки «Сегодня»." ); },
  get coachingFailedNotice() { return t( "Coaching didn't finish this time. Your answer and this outcome are saved, and " + "XP is pending until coaching completes.", "В этот раз разбор не завершился. Ответ и исход сохранены, а XP будет начислён, " + "когда разбор завершится." ); },
  xpAwarded(amount) {
    return `+${amount} XP`
  },
  get needsRetryNotice() { return t( "There wasn't much reasoning to work with this time. A longer answer gives the " + "coaching more to respond to.", "В этот раз аргументации было мало. Более развёрнутый ответ даёт разбору больше " + "материала." ); },
  get strengthsTitle() { return t("What you did well", "Что получилось хорошо"); },
  get improvementsTitle() { return t("What to strengthen", "Что усилить"); },
  get sharperApproach() { return t("A sharper approach", "Более точный подход"); },
  get remediationTitle() { return t("Where to go back to", "К каким урокам вернуться"); },
  get skillImpactTitle() { return t("Skill impact", "Влияние на навыки"); },
  get skillImpactSubtitle() { return t( "Only the skills this challenge touched.", "Только навыки, которых коснулось это задание." ); },
  get wasThisUseful() { return t("Was this useful?", "Это было полезно?"); },
  get useful() { return t("Useful", "Полезно"); },
  get notUseful() { return t("Not useful", "Не полезно"); },
  get ratingThanks() { return t( "Thanks — this helps us improve the coaching.", "Спасибо — это помогает нам улучшать разбор." ); },
  get practiceSignalDisclaimer() { return t( "Skill scores are practice signals based on your in-app work, not an assessment " + "of job readiness.", "Оценки навыков — это сигналы о вашей практике в приложении, а не оценка " + "готовности к работе." ); },
  get finish() { return t("Finish", "Завершить"); },
  get coachingDidntFinish() { return t("Coaching didn't finish", "Разбор не завершился"); },
  get coachingTakingLonger() { return t("Coaching is taking longer", "Разбор занимает больше времени"); },
  get coachingStillPending() { return t("Coaching still pending", "Разбор ещё готовится"); },
  get unavailableBody() { return t( "Your answer is saved and your XP is pending until coaching completes. Nothing " + "is lost — you can come back to this from Progress.", "Ответ сохранён, а XP будет начислён после завершения разбора. Ничего не " + "потеряно — вернуться сюда можно из вкладки «Прогресс»." ); },
  scoreAccessibility(score, band) {
    return t(
    `Score ${score} out of 100. ${band}.`,
    `Оценка ${score} из 100. ${band}.`
    )
  },
  breakdownAccessibility(label, value, max) {
    return t(`${label}: ${value} out of ${max}`, `${label}: ${value} из ${max}`)
  },
  skillImpactAccessibility(label, delta, score) {
    return t(
    `${label} changed by ${delta}, now ${score}`,
    `${label}: изменение ${delta}, теперь ${score}`
    )
  },
},
Progress: {
  get title() { return t("Progress", "Прогресс"); },
  get loadFailed() { return t("Couldn't load progress", "Не удалось загрузить прогресс"); },
  level(value) {
    return t(`Level ${value}`, `Уровень ${value}`)
  },
  get levelLabel() { return t("Level", "Уровень"); },
  totalXp(value) {
    return t(`${value} XP total`, `Всего ${value} XP`)
  },
  get totalXpPrefix() { return t("", "Всего "); },
  get totalXpSuffix() { return t(" XP total", " XP"); },
  xpToNextLevel(remaining, level) {
    return t(
    `${remaining} XP to level ${level}`,
    `${remaining} XP до уровня ${level}`
    )
  },
  get lastSevenDays() { return t("Last 7 days", "Последние 7 дней"); },
  gateHistory(count) {
    return t(
    `${count} gate ${count == 1 ? "attempt" : "attempts"}`,
    `${count} ${plural(count, "попытка", "попытки", "попыток")} на гейтах`
    )
  },
  get blocksPassed() { return t("Blocks passed", "Блоков сдано"); },
  get lessonsRead() { return t("Lessons read", "Уроков пройдено"); },
  get skillsTitle() { return t("Skills", "Навыки"); },
  get skillsSubtitle() { return t( "One competency per domain of the map, plus communication. Trend is based " + "on your last five gates.", "По одной компетенции на домен карты плюс коммуникация. Тренд считается по " + "последним пяти гейтам." ); },
},
History: {
  get title() { return t("History", "История"); },
  get loadFailed() { return t("Couldn't load history", "Не удалось загрузить историю"); },
  get emptyTitle() { return t("No gates attempted yet", "Гейтов пока не было"); },
  get emptyBody() { return t( "Finish the lessons of a block and take its gate — every sitting shows up here.", "Пройдите уроки блока и сдайте его гейт — каждая попытка появится здесь." ); },
  get passed() { return t("Passed", "Сдан"); },
  get notPassed() { return t("Not passed", "Не сдан"); },
  blockAndAttempt(blockTitle, index) {
    return t(
    `${blockTitle} · attempt ${index}`,
    `${blockTitle} · попытка ${index}`
    )
  },
  get loadMore() { return t("Load more", "Показать ещё"); },
  get coachingReady() { return t("Coaching ready", "Разбор готов"); },
  get feedbackPending() { return t("Feedback pending", "Разбор готовится"); },
  get coachingFailed() { return t("Coaching failed", "Разбор не удался"); },
  get resultTitle() { return t("Result", "Результат"); },
  get resultLoadFailed() { return t("Couldn't load result", "Не удалось загрузить результат"); },
  get pendingXpNote() { return t( "Your answer is saved. XP is pending until coaching completes.", "Ответ сохранён. XP будет начислён после завершения разбора." ); },
},
Profile: {
  get title() { return t("Profile", "Профиль"); },
  get practiceSection() { return t("Your practice", "Ваша практика"); },
  get level() { return t("Level", "Уровень"); },
  get totalXp() { return t("Total XP", "Всего XP"); },
  get targetRole() { return t("Target role", "Целевая роль"); },
  get roleSection() { return t("Role", "Роль"); },
  get roleFooter() { return t( "A highlight over the map, nothing more: it does not change the order blocks " + "open in or what a gate asks of you.", "Это только подсветка на карте: порядок открытия блоков и требования гейта " + "она не меняет." ); },
  get languageSection() { return t("Language", "Язык"); },
  get languageLabel() { return t("Interface language", "Язык интерфейса"); },
  get languageFooter() { return t( "Changes everything: the app's own text, scenario briefs and evidence, the " + "consequences, and the coaching you get back. Results you have already " + "finished are shown in the new language too.", "Меняет всё: тексты приложения, описания сценариев и данные, последствия и " + "разбор, который вы получаете. Уже завершённые результаты тоже " + "показываются на новом языке." ); },
  get privacySection() { return t("Privacy", "Приватность"); },
  get privacyNotice() { return t("Privacy notice", "О приватности"); },
  get developerSection() { return t("Developer", "Разработка"); },
  get apply() { return t("Apply", "Применить"); },
  get developerFooter() { return t( "Point the app at a different API host. Debug builds only. Restart the app " + "after changing this.", "Направить приложение на другой API-хост. Только в debug-сборках. После " + "изменения перезапустите приложение." ); },
  get signOut() { return t("Sign out", "Выйти"); },
  get signOutQuestion() { return t("Sign out?", "Выйти из аккаунта?"); },
  get signOutMessage() { return t( "Any draft that hasn't synced yet will be cleared from this device.", "Черновики, которые ещё не синхронизировались, будут удалены с этого устройства." ); },
  get deleteAccount() { return t("Delete account", "Удалить аккаунт"); },
  get deleteQuestion() { return t("Delete your account?", "Удалить ваш аккаунт?"); },
  get deletePermanently() { return t("Delete permanently", "Удалить навсегда"); },
  get deleteMessage() { return t( "This removes your responses, feedback and identity link. It cannot be undone.", "Это удалит ваши ответы, разборы и связь с учётной записью. Отменить нельзя." ); },
  get deleteFooter() { return t( "Deleting your account removes your written responses, your feedback, and your " + "identity link. This cannot be undone.", "Удаление аккаунта убирает ваши письменные ответы, разборы и связь с учётной " + "записью. Отменить это нельзя." ); },
  get deleting() { return t("Deleting your account…", "Удаляем ваш аккаунт…"); },
  version(version, build) {
    return t(`Version ${version} (${build})`, `Версия ${version} (${build})`)
  },
},
Errors: {
  get offline() { return t( "You're offline. Your work is saved on this device and will sync when you " + "reconnect.", "Вы офлайн. Работа сохранена на устройстве и синхронизируется при подключении." ); },
  get timedOut() { return t( "That took too long. Check your connection and try again.", "Это заняло слишком много времени. Проверьте соединение и повторите." ); },
  get unauthorized() { return t( "Your session expired. Sign in again to continue.", "Сессия истекла. Войдите снова, чтобы продолжить." ); },
  get notAvailable() { return t( "That challenge isn't available on this account.", "Это задание недоступно для вашего аккаунта." ); },
  get onboardingIncomplete() { return t( "Finish setting up your account to see today's challenge.", "Завершите настройку аккаунта, чтобы увидеть сегодняшнее задание." ); },
  get alreadySubmitted() { return t( "That's already been submitted. Pull to refresh for the latest state.", "Это уже отправлено. Потяните вниз, чтобы обновить состояние." ); },
  get noEvidenceReviewed() { return t( "Open at least one signal before making a decision.", "Откройте хотя бы один сигнал, прежде чем принимать решение." ); },
  rationaleLength(minimum, maximum) {
    return t(
    `Your reasoning needs to be between ${minimum} and ${maximum} characters.`,
    `Аргументация должна быть от ${minimum} до ${maximum} символов.`
    )
  },
  get invalidSubmission() { return t( "Something in that submission wasn't valid. Check your answer and try again.", "Что-то в отправке оказалось некорректным. Проверьте ответ и повторите." ); },
  get rateLimited() { return t( "You've reached today's coaching limit. Try again tomorrow.", "Вы исчерпали дневной лимит разборов. Попробуйте завтра." ); },
  get noScenarioAvailable() { return t( "Today's challenge isn't ready yet. Try again in a moment.", "Сегодняшнее задание ещё не готово. Попробуйте через минуту." ); },
  get serverProblem() { return t( "The server had a problem. Your answer is safe — try again shortly.", "На сервере возникла проблема. Ваш ответ в безопасности — повторите чуть позже." ); },
  get unexpectedResponse() { return t( "Something unexpected came back from the server. Try again shortly.", "С сервера пришло что-то неожиданное. Повторите чуть позже." ); },
},
Labels: {
  level(key) {
    switch (key) {
    case "foundation": return t("Foundation", "Основы")
    case "developing": return t("Developing", "Развитие")
    case "advanced": return t("Advanced", "Продвинутый")
    default: return capitalize(key)
    }
  },
  skill(key, fallback) {
    switch (key) {
    case "discovery": return t("Discovery & Research", "Дискавери и исследования")
    case "value_design": return t("Value & Solution Design", "Ценность и проектирование")
    case "delivery": return t("Development & Delivery", "Разработка и поставка")
    case "marketing": return t("Product Marketing", "Продуктовый маркетинг")
    case "growth": return t("Growth & Experiments", "Рост и эксперименты")
    case "economics": return t("Sales & Economics", "Продажи и экономика")
    case "communication": return t("Communication", "Коммуникация")
    default: return fallback
    }
  },
  band(serverBand) {
    switch (serverBand) {
    case "Strong reasoning": return t(serverBand, "Сильная аргументация")
    case "Solid reasoning": return t(serverBand, "Уверенная аргументация")
    case "Developing reasoning": return t(serverBand, "Растущая аргументация")
    case "Early reasoning": return t(serverBand, "Ранняя аргументация")
    case "Needs a fuller argument": return t(serverBand, "Нужна более полная аргументация")
    default: return serverBand
    }
  },
  evidenceType(key) {
    switch (key) {
    case "quantitative": return t("Data", "Данные")
    case "qualitative": return t("Voices", "Голоса")
    case "technical": return t("Technical", "Технически")
    case "business": return t("Business", "Бизнес")
    default: return capitalize(key)
    }
  },
  trendDescription(trend) {
    switch (trend) {
    case "up": return t("trending up", "растёт")
    case "down": return t("trending down", "снижается")
    default: return t("steady", "без изменений")
    }
  },
  skillAccessibility(score, trend) {
    return t(
    `${score} out of 100, ${S.Labels.trendDescription(trend)}`,
    `${score} из 100, ${S.Labels.trendDescription(trend)}`
    )
  },
  activityState(state) {
    switch (state) {
    case "completed": return t("completed", "выполнено")
    case "today": return t("today", "сегодня")
    case "upcoming": return t("upcoming", "предстоит")
    default: return t("missed", "пропущено")
    }
  },
  Breakdown: {
    get evidence() { return t("Evidence engagement", "Работа с данными"); },
    get decision() { return t("Decision quality", "Качество решения"); },
    get rationale() { return t("Rationale quality", "Качество аргументации"); },
    get communication() { return t("Communication clarity", "Ясность изложения"); },
  },
  State: {
    get start() { return t("Start", "Начать"); },
    get resume() { return t("Continue", "Продолжить"); },
    get review() { return t("Review", "Пересмотреть"); },
    get continueLater() { return t("Continue later", "Продолжить позже"); },
    get coachingInProgress() { return t("Coaching in progress", "Разбор готовится"); },
    get completed() { return t("Completed", "Выполнено"); },
  },
},
Practice: {
  get title() { return t("Practice", "Практика"); },
  get inPreparation() { return t("In preparation", "Готовится"); },
  get tests() { return t("What it tests", "Что проверяет"); },
  get format() { return t("Format", "Формат"); },
  get newTask() { return t("New task", "Новая задача"); },
  get anotherTask() { return t("Another task", "Другая задача"); },
  get writingTask() { return t("Writing a task…", "Пишем задачу…"); },
  get readingAnswer() { return t("Reading your answer…", "Читаем ваш ответ…"); },
  get submit() { return t("Get feedback", "Получить разбор"); },
  get backToTracks() { return t("All tracks", "Все направления"); },
  get theTask() { return t("The task", "Задача"); },
  get constraints() { return t("Constraints", "Ограничения"); },
  get clarifiers() { return t("Clarifying questions", "Уточняющие вопросы"); },
  get clarifiersHint() { return t( "Ask before you answer. What you choose to ask is part of what the review reads.", "Спрашивайте до ответа: что именно вы спросили, разбор тоже читает." ); },
  get ask() { return t("Ask", "Спросить"); },
  get counterLocked() { return t( "Fill in the fields above first — the objection comes after you have committed.", "Сначала заполните поля выше: возражение приходит после того, как позиция занята." ); },
  get yourAnswer() { return t("Your answer", "Ваш ответ"); },
  get timeOnTask() { return t("Time on task", "Время над задачей"); },
  target(minutes) {
    return t(`about ${minutes} min`, `около ${minutes} мин`)
  },
  charactersLeft(count) {
    return t(
    `${count} more characters`,
    `ещё ${count} ${plural(count, "символ", "символа", "символов")}`
    )
  },
  sessionsSaved(count) {
    return t(
    `${count} saved`,
    `${count} ${plural(count, "сохранена", "сохранено", "сохранено")}`
    )
  },
  get feedback() { return t("Feedback", "Разбор"); },
  get byField() { return t("Field by field", "По частям ответа"); },
  get strengths() { return t("What worked", "Что сработало"); },
  get improvements() { return t("What to sharpen", "Что усилить"); },
  get missedQuestion() { return t("The question you didn't ask", "Вопрос, который вы не задали"); },
  get sharperApproach() { return t("A sharper answer", "Как было бы сильнее"); },
  get saved() { return t("Saved sessions", "Сохранённые тренировки"); },
  get savedHint() { return t( "The task, your answer and the review stay together, so you can come back to them.", "Задача, ваш ответ и разбор хранятся вместе — к ним можно вернуться." ); },
  get noSessions() { return t("Nothing saved here yet.", "Здесь пока ничего нет."); },
  get open() { return t("Open", "Открыть"); },
  get delete() { return t("Delete", "Удалить"); },
  get deleteConfirm() { return t("Delete this session for good?", "Удалить эту тренировку насовсем?"); },
  get unanswered() { return t("Not answered", "Без ответа"); },
  get reviewed() { return t("Reviewed", "Разобрано"); },
  get limitReached() { return t( "That is today's practice limit. It resets 24 hours after your first session today.", "На сегодня лимит тренировок исчерпан. Он обновится через сутки после первой сегодняшней." ); },
  get generationFailed() { return t( "The task couldn't be written. Try again in a moment.", "Задачу написать не удалось. Попробуйте через минуту." ); },
  get feedbackFailed() { return t( "The review couldn't be written. Your answer is still here — try again.", "Разбор не получился. Ответ на месте — попробуйте ещё раз." ); },
  get notReady() { return t("This track is still in preparation.", "Это направление ещё готовится."); },
  Bar: {
    get below() { return t("Below the bar", "Ниже планки"); },
    get at() { return t("At the bar", "На уровне планки"); },
    get above() { return t("Above the bar", "Выше планки"); },
  },
},
};
