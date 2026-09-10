import SwiftUI

/// Every user-facing string in the app, in both languages, side by side.
///
/// Grouped by screen so a translation gap is obvious at a glance. Server-authored
/// content (scenario text, briefs, evidence, consequences, coaching) is not here — it
/// arrives already written and is shown as-is.
enum S {

    // MARK: - Shared

    enum Common {
        static var back: String { t("Back", "Назад") }
        static var next: String { t("Next", "Далее") }
        static var continueAction: String { t("Continue", "Продолжить") }
        static var done: String { t("Done", "Готово") }
        static var close: String { t("Close", "Закрыть") }
        static var cancel: String { t("Cancel", "Отмена") }
        static var tryAgain: String { t("Try again", "Повторить") }
        static var loading: String { t("Loading…", "Загрузка…") }
        static var couldntLoad: String { t("Couldn't load", "Не удалось загрузить") }
        /// Только веб: ссылка «к содержанию» для клавиатуры. Живёт здесь, потому что
        /// таблица строк одна на оба клиента и вторая копия разошлась бы на первой правке.
        /// Подпись под логотипом. Только веб: в приложении название несёт иконка.
        static var tagline: String { t("skill map of the craft", "карта навыков профессии") }
        static var skipToContent: String { t("Skip to content", "К содержанию") }
        static var expandMenu: String { t("Expand menu", "Развернуть меню") }
        static var collapseMenu: String { t("Collapse menu", "Свернуть меню") }

        static func minutes(_ count: Int) -> String {
            t("\(count) min", "\(count) мин")
        }

        static func xp(_ count: Int) -> String { "\(count) XP" }

        static func scoreOutOf100(_ score: Int) -> String { "\(score)/100" }

        static func dayStreak(_ count: Int) -> String {
            t(
                "\(count) day streak",
                "\(count) \(plural(count, "день", "дня", "дней")) подряд"
            )
        }
    }

    enum Tab {
        /// Обучение — то, чем занимаются каждый день; карта навыков стала
        /// отдельным разделом, который открывают, когда нужен обзор.
        static var learn: String { t("Learn", "Обучение") }
        static var tree: String { t("Skills Map", "Карта навыков") }
        static var practice: String { t("Practice", "Практика") }
        static var progress: String { t("Progress", "Прогресс") }
        static var profile: String { t("Profile", "Профиль") }
    }

    // MARK: - Welcome & privacy

    enum Welcome {
        static var headline: String {
            t(
                "Practise thinking like a Product Manager.",
                "Тренируйте мышление продакт-менеджера."
            )
        }
        static var subheadline: String {
            t(
                "A short daily product scenario. Your decision. Clear feedback.",
                "Короткий продуктовый сценарий каждый день. Ваше решение. Понятный разбор."
            )
        }
        static var continueWithApple: String {
            t("Continue with Apple", "Продолжить с Apple")
        }
        static var developerSignIn: String {
            t("Continue without Apple (development)", "Продолжить без Apple (для разработки)")
        }
        static var privacyNotice: String { t("Privacy notice", "О приватности") }
    }

    // MARK: - Sign in / sign up

    enum Auth {
        static var signIn: String { t("Sign in", "Вход") }
        static var signUp: String { t("Create account", "Регистрация") }
        static var email: String { t("Email", "Почта") }
        static var password: String { t("Password", "Пароль") }
        static var emailPlaceholder: String { t("you@example.com", "you@example.com") }
        static var continueWithGoogle: String {
            t("Continue with Google", "Продолжить с Google")
        }
        static var or: String { t("or", "или") }

        static var haveAccount: String {
            t("Already have an account? Sign in", "Уже есть аккаунт? Войти")
        }
        static var needAccount: String {
            t("No account yet? Create one", "Нет аккаунта? Создать")
        }

        static func passwordRule(_ minimum: Int) -> String {
            t(
                "At least \(minimum) characters.",
                "Не меньше \(minimum) символов."
            )
        }

        // Ошибки входа названы так, чтобы человек понял, что делать дальше, а не
        // угадывал. «Такой почты нет» мы не говорим осознанно: по этому ответу
        // перебирают чужие адреса.
        static var invalidCredentials: String {
            t(
                "That email and password don't match an account.",
                "Такая пара почты и пароля не подходит."
            )
        }
        static var emailTaken: String {
            t(
                "That email already has an account. Sign in instead.",
                "На эту почту уже есть аккаунт. Войдите."
            )
        }
        static var emailInvalid: String {
            t("That doesn't look like an email address.", "Это не похоже на адрес почты.")
        }
        static var googleUnavailable: String {
            t(
                "Google sign-in isn't set up on this server yet.",
                "Вход через Google на этом сервере пока не настроен."
            )
        }
        static var noMethods: String {
            t(
                "This server has no sign-in method enabled.",
                "На этом сервере не включён ни один способ входа."
            )
        }
    }

    enum Privacy {
        static var title: String { t("Privacy", "Приватность") }
        static var heading: String {
            t("What we collect and why", "Что мы собираем и зачем")
        }

        static var accountTitle: String { t("Your account", "Ваш аккаунт") }
        static var accountBody: String {
            t(
                "Signing in with Apple gives us a stable identifier for your account. We do "
                    + "not ask for your name, email, employer, or any demographic information.",
                "Вход через Apple даёт нам постоянный идентификатор аккаунта. Мы не спрашиваем "
                    + "ваше имя, почту, работодателя и любые демографические данные."
            )
        }

        static var writingTitle: String { t("What you write", "То, что вы пишете") }
        static var writingBody: String {
            t(
                "The reasoning you write for each challenge is sent to our server and to our "
                    + "AI provider for the sole purpose of generating your feedback. It is "
                    + "never sent to analytics, crash reporting, or notifications.",
                "Ваша аргументация по каждому заданию отправляется на наш сервер и AI-провайдеру "
                    + "исключительно для подготовки разбора. Она никогда не попадает в аналитику, "
                    + "отчёты об ошибках или уведомления."
            )
        }

        static var analyticsTitle: String { t("Product analytics", "Продуктовая аналитика") }
        static var analyticsBody: String {
            t(
                "We record which screens you reach and which options you select so we can "
                    + "improve the product. These events never include what you wrote or the "
                    + "feedback you received.",
                "Мы фиксируем, до каких экранов вы дошли и какие варианты выбрали, чтобы "
                    + "улучшать продукт. В этих событиях никогда нет ни ваших текстов, ни "
                    + "полученного разбора."
            )
        }

        static var deletionTitle: String { t("Deleting your account", "Удаление аккаунта") }
        static var deletionBody: String {
            t(
                "You can delete your account from Profile at any time. This removes your "
                    + "written responses, your feedback, and your identity link.",
                "Аккаунт можно удалить в Профиле в любой момент. Вместе с ним удаляются ваши "
                    + "ответы, разборы и связь с вашей учётной записью."
            )
        }

        static var scoresTitle: String { t("What scores mean", "Что означают оценки") }
        static var scoresBody: String {
            t(
                "Skill scores are practice signals based on your in-app work. They are not an "
                    + "assessment of job readiness and they do not predict hiring outcomes.",
                "Оценки навыков — это сигналы о вашей практике в приложении. Это не оценка "
                    + "готовности к работе и не прогноз результатов найма."
            )
        }
    }

    // MARK: - Skill tree

    enum Tree {
        static var loading: String { t("Loading the map…", "Загружаем карту…") }
        static var loadFailed: String {
            t("Couldn't load the map", "Не удалось загрузить карту")
        }
        static var continueHere: String { t("Continue here", "Продолжить здесь") }
        static var openBlock: String { t("Open block", "Открыть блок") }
        static var tiersTitle: String { t("Three levels", "Три уровня") }
        static var tiersSubtitle: String {
            t(
                "The level is how much uncertainty the task carries, not how hard it is.",
                "Уровень — это степень неопределённости задачи, а не её сложность."
            )
        }
        static var domainsTitle: String { t("Six domains", "Шесть доменов") }
        static var domainsSubtitle: String {
            t(
                "Everything is visible from day one. Only the route is earned.",
                "Всё видно с первого дня. Зарабатывается только маршрут."
            )
        }
        static var comingSoon: String {
            t(
                "The lessons for this block are still being written.",
                "Уроки этого блока ещё пишутся."
            )
        }
        static var lessonsComingSoon: String {
            t("Lesson coming soon", "Урок скоро появится")
        }
        /// Раздел «Обучение».
        static var currentDirection: String { t("Now studying", "Сейчас изучаете") }
        static var continueLesson: String { t("Continue", "Продолжить") }
        static var blockLessonsTitle: String { t("Lessons of this block", "Уроки этого блока") }
        static var gateLocked: String {
            t("Opens after the lessons", "Откроется после уроков")
        }
        static var noDirectionYet: String {
            t("Nothing started here yet", "Здесь вы ещё не начинали")
        }

        static func blocksProgress(_ passed: Int, _ total: Int) -> String {
            t("\(passed) of \(total) blocks", "\(passed) из \(total) блоков")
        }

        static var blockGoalTitle: String {
            t("What this block gives you", "Что даёт этот блок")
        }
        static var blockGoalSubtitle: String {
            t(
                "Each question below is one skill. The gate at the end asks you to use them, not to recall them.",
                "Каждый вопрос ниже — один навык. Гейт в конце просит их применить, а не вспомнить."
            )
        }
        static var lessonsTitle: String { t("Lessons", "Уроки") }
        /// Общее начало карты: одна точка, из которой расходятся все шесть ветвей.
        static var startNode: String { t("Start", "Начало") }
        /// Номер таблицы под картой: карта — это изданная схема, и подпись под ней
        /// набирается как в справочнике, а не как служебная строка.
        static func plateNumber(_ number: Int) -> String {
            t("Plate \(number)", "Табл. \(number)")
        }
        /// Подпись под счётчиком в середине карты: знаменатель, а не единица
        /// измерения — «из скольких» здесь важнее слова «уроков».
        static func skillsLearned(_ total: Int) -> String {
            t("of \(total) learned", "из \(total) освоено")
        }
        static var zoomIn: String { t("Zoom in", "Приблизить") }
        static var zoomOut: String { t("Zoom out", "Отдалить") }
        static var zoomReset: String { t("Fit the map", "Вся карта") }
        static var openLesson: String { t("Open lesson", "Открыть урок") }
        static var mapHint: String {
            t(
                "Drag to move, scroll to zoom. A card is one skill — open it to read its lesson.",
                "Тяните, чтобы двигать, колесо — масштаб. Карточка — один навык, в ней урок."
            )
        }

        static func lessonsInNode(_ count: Int) -> String {
            t(
                "\(count) lessons",
                "\(count) \(plural(count, "урок", "урока", "уроков"))"
            )
        }

        static var legendLesson: String { t("Lesson", "Урок") }
        static var legendLessonDone: String { t("Lesson done", "Урок пройден") }
        static var legendGate: String { t("Block gate", "Гейт блока") }
        static var gateTitle: String { t("Gate", "Гейт") }
        static var gateHeadline: String {
            t("One situation, not a test", "Одна ситуация вместо теста")
        }
        static var gatePitch: String {
            t(
                "A real situation with incomplete data. You make the call and argue it in writing.",
                "Настоящая ситуация с неполными данными. Вы принимаете решение и обосновываете его письменно."
            )
        }
        static var gateNoPenalty: String {
            t(
                "Failing costs nothing: no XP is taken away and nothing closes.",
                "Провал ничего не стоит: XP не отнимается и ничего не закрывается."
            )
        }

        static func blockSummary(_ nodes: Int, lessons: Int, minutes: Int) -> String {
            t(
                "\(nodes) skills · \(lessons) lessons · about \(minutes) min",
                "\(nodes) \(plural(nodes, "навык", "навыка", "навыков")) · "
                    + "\(lessons) \(plural(lessons, "урок", "урока", "уроков")) · около \(minutes) мин"
            )
        }

        static func lessonNumber(_ index: Int) -> String {
            t("Lesson \(index)", "Урок \(index)")
        }
        static var takeGate: String { t("Take the gate", "Сдать гейт") }
        static var retakeGate: String { t("Take it again", "Пересдать") }

        static func gateSubtitle(_ threshold: Int) -> String {
            t(
                "A situation with incomplete data, not a test. \(threshold) out of 100 to pass.",
                "Ситуация с неполными данными, а не тест. Для зачёта нужно \(threshold) из 100."
            )
        }

        static func gateBlockedReason(_ reason: String?, remaining: Int) -> String {
            switch reason {
            case "locked":
                return t(
                    "Pass the previous block to open this one.",
                    "Сдайте предыдущий блок, чтобы открыть этот."
                )
            case "coming_soon":
                return comingSoon
            case "lessons_remaining":
                return t(
                    "\(remaining) more \(remaining == 1 ? "lesson" : "lessons") to finish first.",
                    "Осталось пройти \(remaining) \(plural(remaining, "урок", "урока", "уроков"))."
                )
            default:
                return t("Not available yet.", "Пока недоступно.")
            }
        }

        static func lockedExplanation(_ prerequisites: [String]) -> String {
            let list = prerequisites.joined(separator: ", ")
            return t(
                "Opens once you pass \(list).",
                "Откроется, когда вы сдадите \(list)."
            )
        }

        static func lessonsProgress(_ done: Int, _ total: Int) -> String {
            t(
                "\(done) of \(total) lessons read",
                "Пройдено \(done) из \(total) \(plural(total, "урока", "уроков", "уроков"))"
            )
        }

        static func ofBlocks(_ total: Int) -> String {
            t("of \(total)", "из \(total)")
        }

        static func passedOfTotal(_ passed: Int, _ total: Int) -> String {
            t(
                "\(passed) of \(total) blocks passed",
                "Сдано \(passed) из \(total) \(plural(total, "блока", "блоков", "блоков"))"
            )
        }

        /// Запасное название круга, когда контент ещё не загружен.
        ///
        /// Латиницей в обоих языках намеренно: «Уровень 1» столкнулся бы с уровнем
        /// XP, который показан рядом — в Прогрессе и в боковой панели.
        static func tierName(_ tier: Int) -> String {
            "Level \(tier)"
        }

        static func tierSubtitle(_ tier: Int) -> String {
            switch tier {
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
        }

        static func statusLabel(_ status: BlockStatus) -> String {
            switch status {
            case .locked: return t("Locked", "Закрыт")
            case .available: return t("Open", "Открыт")
            case .inProgress: return t("In progress", "В процессе")
            case .gateReady: return t("Ready for the gate", "Готов к гейту")
            case .passed: return t("Passed", "Сдан")
            }
        }

        static func statusSymbol(_ status: BlockStatus) -> String {
            switch status {
            case .locked: return "lock.fill"
            case .available: return "circle"
            case .inProgress: return "circle.lefthalf.filled"
            case .gateReady: return "flag.fill"
            case .passed: return "checkmark.circle.fill"
            }
        }

        static func statusTint(_ status: BlockStatus) -> Color {
            switch status {
            case .locked: return Theme.Palette.tertiaryText
            case .available, .inProgress: return Theme.Palette.secondaryText
            case .gateReady: return Theme.Palette.accent
            case .passed: return Theme.Palette.positive
            }
        }

        /// VoiceOver has to convey what the rings convey visually: which domain, which
        /// ring, and what state the block is in (spec v0.2 §14).
        static func blockAccessibility(_ block: BlockSummary, tree: TreeResponse) -> String {
            let domain = tree.domains.first { $0.key == block.domainKey }?.title ?? block.domainKey
            return "\(domain), \(tierName(block.tier)). \(block.title). "
                + "\(statusLabel(block.status)). "
                + lessonsProgress(block.lessonsCompleted, block.lessonsTotal)
        }
    }

    // MARK: - Lesson

    enum Lesson {
        static var takeaway: String { t("The point", "Главное") }
        static var checkYourself: String { t("Check yourself", "Проверьте себя") }
        static var checkNotScored: String {
            t(
                "Not scored — the gate is where application is checked.",
                "Не оценивается: применение проверяет гейт."
            )
        }
        static var example: String { t("Example", "Пример") }
        static var terms: String { t("Terms in this lesson", "Термины урока") }
        static var exercise: String { t("Exercise", "Упражнение") }
        static var markRead: String { t("Mark as read", "Отметить как прочитанное") }
        // Обзор — это разговор о материале урока, а не урок вслух. Название обещает
        // именно разговор, иначе слушатель ждёт дословного чтения и обманывается.
        static var audioTitle: String { t("Audio overview", "Аудиообзор") }
        static var audioSubtitle: String {
            t("Two hosts discuss this lesson", "Двое обсуждают этот урок")
        }
        static var audioLoading: String { t("Preparing…", "Готовлю…") }
        static var audioFailed: String { t("Could not load. Tap to retry.", "Не удалось загрузить. Нажмите ещё раз.") }
        static var audioPlay: String { t("Play", "Слушать") }
        static var audioPause: String { t("Pause", "Пауза") }
        static var audioBack15: String { t("Back 15 seconds", "Назад на 15 секунд") }
        static var audioForward15: String { t("Forward 15 seconds", "Вперёд на 15 секунд") }
        static var audioSpeed: String { t("Speed", "Скорость") }
        static var audioPosition: String { t("Position", "Позиция") }
        // Сборка обзора — авторский режим, в релизной сборке этих строк не видно.
        static var audioBuild: String { t("Generate overview", "Сгенерировать обзор") }
        static var audioBuilding: String {
            t("Writing and voicing… about a minute", "Пишу и озвучиваю… около минуты")
        }
        static var audioBuildFailed: String {
            t("Generation failed. Tap to retry.", "Не получилось. Нажмите, чтобы повторить.")
        }
        static var nextLesson: String { t("Next lesson", "Следующий урок") }
        static var backToBlock: String { t("Back to the block", "Вернуться к блоку") }
    }

    enum Glossary {
        static var title: String { t("Glossary", "Глоссарий") }
        static var searchPrompt: String {
            t("Search in Russian or English", "Поиск по-русски или по-английски")
        }
        static var empty: String { t("Nothing found", "Ничего не нашлось") }
        static var seen: String { t("Seen in a lesson", "Встречали в уроке") }
        static var openLesson: String { t("Read the lesson", "Открыть урок") }
    }

    enum Exercise {
        static var title: String { t("Exercise", "Упражнение") }
        static var check: String { t("Check", "Проверить") }
        static var showReference: String {
            t("Skip and see the reasoning", "Пропустить и посмотреть разбор")
        }
        static var reference: String { t("How to think about it", "Как рассуждать") }
        // Упражнение не оценивает: кнопка завершает пониманием, а не счётом.
        static var understood: String { t("Got it", "Понятно") }
        static var orderRight: String { t("Order of magnitude is right", "Порядок верный") }
        static var orderOff: String { t("Order of magnitude differs", "Порядок отличается") }
        // Для разбора по категориям «порядок» ничего не значит, а «неправильно» —
        // оценка, которой у формирующего упражнения быть не должно.
        static var sameAsReference: String { t("Same as the reasoning", "Как в разборе") }
        static var otherThanReference: String {
            t("Differs from the reasoning", "Иначе, чем в разборе")
        }
        static var notAnswered: String { t("Not answered", "Без ответа") }
        static var chooseAnswer: String { t("Choose", "Выберите") }
    }

    // MARK: - Learn

    /// Объяснение карты на главном экране. Шесть областей System Design
    /// описаны здесь же: у них в контенте есть ключевой вопрос, и абзац
    /// строится вокруг него.
    enum Learn {
        static var learnMore: String { t("Learn more", "Подробнее") }
        static var blocksTitle: String { t("Blocks of this direction", "Блоки направления") }

        static func intro(_ kind: String) -> String {
            kind == "system_design"
                ? t(
                    "Six areas of how a product works inside. A product manager does not build them, but every one of them sets a limit on what can be promised and how fast.",
                    "Шесть областей того, как продукт устроен внутри. Продакт их не строит, но каждая ставит границу тому, что можно пообещать и как быстро."
                )
                : t(
                    "Six directions are not chapters of a course. They are the competencies a product manager is made of: each owns its part of the work, and together they cover the way from research to money.",
                    "Шесть направлений — это не разделы курса, а составляющие компетенции продакта: каждое отвечает за свой кусок работы, и вместе они покрывают путь от исследования до денег."
                )
        }

        static func aboutTitle(_ kind: String) -> String {
            kind == "system_design"
                ? t("How the systems map works", "Как устроена карта систем")
                : t("How the skill map works", "Как устроена карта навыков")
        }

        static func aboutLead(_ kind: String) -> String {
            kind == "system_design"
                ? t(
                    "The job here is not to design systems but to understand the price of a decision: what a promise costs, what it takes to change, and what breaks under load. Six areas, three levels of uncertainty — the same grammar as the product map.",
                    "Задача здесь не проектировать системы, а понимать цену решения: сколько стоит обещание, чего стоит его изменить и что ломается под нагрузкой. Шесть областей, три уровня неопределённости — та же грамматика, что и у карты продукта."
                )
                : t(
                    "A product manager's job is to get the most value to people with the least time to market. That work does not split into one skill — it splits into six directions, and inside each one the skills differ by how much uncertainty you carry.",
                    "Работа продакта — довести до людей максимум ценности за минимум времени до рынка. Эта работа не сводится к одному навыку: она делится на шесть направлений, а внутри каждого навыки отличаются тем, сколько неопределённости вы несёте."
                )
        }

        static func levelAudience(_ tier: Int) -> String {
            switch tier {
            case 1: return t("Junior level · a single task or feature", "Junior · одиночная задача или фича")
            case 2: return t("Middle and senior level · a project or a product vertical", "Middle и senior · проект или вертикаль продукта")
            default: return t("Senior, head of product, CPO · a product or a portfolio", "Senior, head of product, CPO · продукт или портфель")
            }
        }

        static func domainBlurb(_ key: String) -> String {
            switch key {
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
        }

        static func sourceNote(_ kind: String) -> String {
            kind == "system_design"
                ? t(
                    "The systems map extends the product one and follows its grammar.",
                    "Карта систем расширяет продуктовую и следует её грамматике."
                )
                : t(
                    "Six directions, three levels: one grammar for the whole profession.",
                    "Шесть направлений и три уровня — одна грамматика на всю профессию."
                )
        }
    }

    enum Trees {
        static var product: String { t("Product", "Продукт") }
        static var systems: String { t("Systems", "Системы") }
        static var recommendation: String {
            t(
                "New to product? Start with Discovery in the product map.",
                "Если вы новичок — начните с первого блока карты продукта."
            )
        }
    }

    // MARK: - Roles

    enum Roles {
        // Product Manager first: it is the role that spans the whole map.
        static let keys = [
            "product_manager", "product_analyst", "growth_manager", "scrum_product_owner",
            "head_of_product", "product_marketing_manager", "product_designer",
            "project_manager", "cpo", "cmo",
        ]

        static var none: String { t("Not chosen", "Не выбрана") }

        static func title(_ key: String?) -> String {
            switch key {
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
            default: return none
            }
        }
    }

    // MARK: - Onboarding

    enum Onboarding {
        static var setUpTitle: String { t("Getting started", "Начало") }

        static var howItWorksTitle: String {
            t("A route, not a library", "Маршрут, а не библиотека")
        }
        static var howItWorksSubtitle: String {
            t(
                "The map of the profession, turned into a path you can walk from zero. "
                    + "Five things worth knowing before the first lesson.",
                "Карта профессии, превращённая в путь, который можно пройти с нуля. "
                    + "Пять вещей, которые стоит знать до первого урока."
            )
        }

        static var stepMapTitle: String { t("Two maps, both open", "Две карты, обе открыты") }
        static var stepMapBody: String {
            t(
                "The product map — 71 skills — and System Design — 96 — share one grammar "
                    + "and one switch at the top. Everything is open from day one: start "
                    + "at the first block of the product map if you are new, or anywhere else.",
                "Карта продукта — 71 навык — и System Design — 96 — устроены одинаково и "
                    + "переключаются наверху экрана. Всё открыто с первого дня: если вы "
                    + "новичок, начните с первого блока карты продукта, но можно и с любого места."
            )
        }

        // Кольца путали: «Junior / Middle / Senior» читалось как оценка человека,
        // хотя означает неопределённость задачи. Теперь это сказано прямо.
        static var stepRingsTitle: String {
            t("Rings are uncertainty, not seniority", "Кольца — это неопределённость, а не грейд")
        }
        static var stepRingsBody: String {
            t(
                "The inner ring is a task someone already framed for you. The outer one is "
                    + "where you choose the frame. It says nothing about how good a manager "
                    + "you are.",
                "Внутреннее кольцо — задача, которую уже поставили за вас. Внешнее — то, где "
                    + "рамку выбираете вы. К оценке вас как менеджера это отношения не имеет."
            )
        }

        static var stepLessonsTitle: String { t("Short lessons", "Короткие уроки") }
        static var stepLessonsBody: String {
            t(
                "One idea, one model, and where it stops working: three to five minutes on "
                    + "the product map, twelve to fifteen in System Design. Some carry an "
                    + "audio overview — two hosts talking the lesson through, not reading it "
                    + "aloud.",
                "Одна идея, одна модель и границы, за которыми она не работает: три-пять "
                    + "минут на карте продукта, двенадцать-пятнадцать в System Design. У части "
                    + "уроков есть аудиообзор — двое ведущих обсуждают материал, а не читают "
                    + "его вслух."
            )
        }

        static var stepGateTitle: String { t("A gate, not a quiz", "Гейт, а не тест") }
        static var stepGateBody: String {
            t(
                "Each block ends in a real situation with incomplete data. You decide and "
                    + "defend the decision in writing — the reasoning is most of the score, "
                    + "so no option is «the right answer» on its own.",
                "Каждый блок заканчивается настоящей ситуацией с неполными данными. Вы "
                    + "принимаете решение и обосновываете его письменно — аргументация даёт "
                    + "большую часть баллов, поэтому «правильного варианта» самого по себе тут нет."
            )
        }

        static var stepUnlockTitle: String {
            t("Failing costs nothing", "Несданный гейт ничего не стоит")
        }
        static var stepUnlockBody: String {
            t(
                "No XP is taken away and nothing locks. A failed gate sends you back to the "
                    + "exact lessons that would have helped, and you can retake it — the "
                    + "second sitting is a different situation, so it cannot be passed from "
                    + "memory.",
                "XP не отнимается и ничего не закрывается. Несданный гейт возвращает вас к "
                    + "конкретным урокам, которых не хватило, и его можно пересдать — во "
                    + "второй раз ситуация другая, поэтому пройти его по памяти нельзя."
            )
        }

        static var ownPace: String {
            t(
                "No daily limits and no streaks to lose. Ten minutes on the metro or an "
                    + "hour at the weekend — both work.",
                "Никаких дневных лимитов и стриков, которые можно потерять. Десять минут в "
                    + "метро или час на выходных — оба варианта рабочие."
            )
        }

        static var roleTitle: String { t("Aiming at a role?", "Метите в конкретную роль?") }
        static var roleSubtitle: String {
            t(
                "It highlights part of the map. It changes nothing about the order, and you "
                    + "can skip it or change it later.",
                "Она подсветит часть карты. Порядок это не меняет, и её можно пропустить или "
                    + "поменять позже."
            )
        }
        static var startLearning: String { t("Start learning", "Начать учиться") }
        static var skipRole: String { t("Skip for now", "Пропустить") }
    }

    // MARK: - Challenge

    enum Challenge {

        enum Step {
            static var situation: String { t("The situation", "Ситуация") }
            static var investigate: String { t("Investigate", "Разобраться") }
            static var decide: String { t("Decide & defend", "Решить и обосновать") }
            static var consequence: String { t("What happens next", "Что происходит дальше") }
            static var feedback: String { t("Coaching", "Разбор") }
        }

        static var loadingScenario: String {
            t("Loading the scenario…", "Загружаем сценарий…")
        }
        static func stepProgress(_ current: Int, _ total: Int) -> String {
            t("Step \(current) of \(total)", "Шаг \(current) из \(total)")
        }
        static var leaveTitle: String {
            t("Leave this challenge?", "Выйти из задания?")
        }
        static var saveAndLeave: String { t("Save and leave", "Сохранить и выйти") }
        static var keepWorking: String { t("Keep working", "Продолжить работу") }
        static var leaveMessage: String {
            t(
                "Your work is saved. You can pick it up from Today.",
                "Работа сохранена. Вернуться к ней можно из вкладки «Сегодня»."
            )
        }

        // Brief
        static var yourRole: String { t("Your role", "Ваша роль") }
        static var theCompany: String { t("The company", "Компания") }
        static var whatsHappening: String { t("What's happening", "Что происходит") }
        static var theObjective: String { t("The objective", "Цель") }
        static var constraints: String { t("Constraints", "Ограничения") }
        static var yourTask: String { t("Your task", "Ваша задача") }
        static var whatGoodLooksLike: String {
            t("What good looks like", "Как выглядит хороший ответ")
        }

        // Investigate
        static var investigatePrompt: String {
            t("What do you want to look at?", "На что хотите посмотреть?")
        }
        static func evidenceCounter(_ reviewed: Int, _ total: Int) -> String {
            t(
                "\(reviewed) of \(total) signals reviewed",
                "Изучено \(reviewed) из \(total) \(plural(total, "сигнала", "сигналов", "сигналов"))"
            )
        }
        static var partialEvidenceNotice: String {
            t(
                "This is everything you get. Real decisions are made on partial evidence — say "
                    + "what you can't know as well as what you can.",
                "Это все данные, что у вас есть. Настоящие решения принимаются на неполных "
                    + "данных — скажите и о том, чего знать нельзя, а не только о том, что знаете."
            )
        }
        static var openOneSignal: String {
            t(
                "Open at least one signal before deciding.",
                "Откройте хотя бы один сигнал, прежде чем решать."
            )
        }
        static var makeADecision: String { t("Make a decision", "Принять решение") }
        static var reviewed: String { t("Reviewed", "Изучено") }
        static var opensSignal: String { t("Opens this signal", "Открывает этот сигнал") }
        static var collapsesSignal: String {
            t("Collapses this signal", "Сворачивает этот сигнал")
        }

        // Decide
        static var severalAnswers: String {
            t(
                "Several answers can be defended. What matters is the reasoning.",
                "Обосновать можно несколько вариантов. Важна именно аргументация."
            )
        }
        static var defendYourDecision: String {
            t("Defend your decision", "Обоснуйте своё решение")
        }
        static var rationalePlaceholder: String {
            t(
                "What evidence, trade-off, and risk informed your choice?",
                "Какие данные, компромиссы и риски привели вас к этому выбору?"
            )
        }
        static var yourReasoning: String { t("Your reasoning", "Ваша аргументация") }
        static var longEnough: String { t("Long enough", "Достаточно длинно") }
        static var saved: String { t("Saved", "Сохранено") }
        static var offlineDraft: String {
            t(
                "Saved on this device. It will sync when you're back online — you can't submit "
                    + "until it does.",
                "Сохранено на этом устройстве. Синхронизируется, когда вы вернётесь в сеть — "
                    + "до этого отправить нельзя."
            )
        }
        static var reasoningNotOptionNote: String {
            t(
                "Feedback assesses your reasoning, not only which option you picked.",
                "Разбор оценивает вашу аргументацию, а не только выбранный вариант."
            )
        }
        static var submitDecision: String { t("Submit decision", "Отправить решение") }

        static func charactersToGo(_ count: Int) -> String {
            t(
                "\(count) more characters to go.",
                "Осталось \(count) \(plural(count, "символ", "символа", "символов"))."
            )
        }
        static func charactersOver(_ count: Int) -> String {
            t(
                "\(count) characters over the limit.",
                "\(count) \(plural(count, "символ", "символа", "символов")) сверх лимита."
            )
        }

        // Consequence
        static var youChose: String { t("You chose", "Вы выбрали") }
        static var whatHappensNext: String { t("What happens next", "Что происходит дальше") }
        static var whatHappenedNext: String { t("What happened next", "Что произошло дальше") }
        static var loadingOutcome: String { t("Loading the outcome…", "Загружаем исход…") }
        static var seeCoaching: String { t("See coaching", "Посмотреть разбор") }
        static var retryCoaching: String { t("Retry coaching", "Повторить разбор") }
        static var preparingCoaching: String { t("Preparing coaching…", "Готовим разбор…") }
        static var checkAgain: String { t("Check again", "Проверить снова") }
        static var coachingReady: String { t("Your coaching is ready.", "Ваш разбор готов.") }
        static var coachingPending: String {
            t(
                "Coaching is taking a moment. Your answer is saved — you can leave and come "
                    + "back to it from Today.",
                "Разбор занимает чуть больше времени. Ответ сохранён — можно выйти и вернуться "
                    + "к нему из вкладки «Сегодня»."
            )
        }
        static var coachingFailedNotice: String {
            t(
                "Coaching didn't finish this time. Your answer and this outcome are saved, and "
                    + "XP is pending until coaching completes.",
                "В этот раз разбор не завершился. Ответ и исход сохранены, а XP будет начислён, "
                    + "когда разбор завершится."
            )
        }

        // Feedback
        static func xpAwarded(_ amount: Int) -> String { "+\(amount) XP" }
        static var needsRetryNotice: String {
            t(
                "There wasn't much reasoning to work with this time. A longer answer gives the "
                    + "coaching more to respond to.",
                "В этот раз аргументации было мало. Более развёрнутый ответ даёт разбору больше "
                    + "материала."
            )
        }
        static var strengthsTitle: String { t("What you did well", "Что получилось хорошо") }
        static var improvementsTitle: String { t("What to strengthen", "Что усилить") }
        static var sharperApproach: String { t("A sharper approach", "Более точный подход") }
        // Провал — это информация: сервер всегда присылает `remediation` с конкретными
        // уроками, и разбор должен показать их, а не оставить человека с одним числом.
        static var remediationTitle: String {
            t("Where to go back to", "К каким урокам вернуться")
        }
        static var skillImpactTitle: String { t("Skill impact", "Влияние на навыки") }
        static var skillImpactSubtitle: String {
            t(
                "Only the skills this challenge touched.",
                "Только навыки, которых коснулось это задание."
            )
        }
        static var wasThisUseful: String { t("Was this useful?", "Это было полезно?") }
        static var useful: String { t("Useful", "Полезно") }
        static var notUseful: String { t("Not useful", "Не полезно") }
        static var ratingThanks: String {
            t(
                "Thanks — this helps us improve the coaching.",
                "Спасибо — это помогает нам улучшать разбор."
            )
        }
        static var practiceSignalDisclaimer: String {
            t(
                "Skill scores are practice signals based on your in-app work, not an assessment "
                    + "of job readiness.",
                "Оценки навыков — это сигналы о вашей практике в приложении, а не оценка "
                    + "готовности к работе."
            )
        }
        static var finish: String { t("Finish", "Завершить") }
        static var coachingDidntFinish: String {
            t("Coaching didn't finish", "Разбор не завершился")
        }
        static var coachingTakingLonger: String {
            t("Coaching is taking longer", "Разбор занимает больше времени")
        }
        static var coachingStillPending: String {
            t("Coaching still pending", "Разбор ещё готовится")
        }
        static var unavailableBody: String {
            t(
                "Your answer is saved and your XP is pending until coaching completes. Nothing "
                    + "is lost — you can come back to this from Progress.",
                "Ответ сохранён, а XP будет начислён после завершения разбора. Ничего не "
                    + "потеряно — вернуться сюда можно из вкладки «Прогресс»."
            )
        }

        static func scoreAccessibility(_ score: Int, band: String) -> String {
            t(
                "Score \(score) out of 100. \(band).",
                "Оценка \(score) из 100. \(band)."
            )
        }
        static func breakdownAccessibility(_ label: String, _ value: Int, _ max: Int) -> String {
            t("\(label): \(value) out of \(max)", "\(label): \(value) из \(max)")
        }
        static func skillImpactAccessibility(_ label: String, _ delta: Int, _ score: Int) -> String {
            t(
                "\(label) changed by \(delta), now \(score)",
                "\(label): изменение \(delta), теперь \(score)"
            )
        }
    }

    // MARK: - Progress & history

    enum Progress {
        static var title: String { t("Progress", "Прогресс") }
        static var loadFailed: String {
            t("Couldn't load progress", "Не удалось загрузить прогресс")
        }
        static func level(_ value: Int) -> String { t("Level \(value)", "Уровень \(value)") }
        /// Подпись над цифрой уровня. Веб-клиент печатает уровень как показатель,
        /// а не как заголовок: одинаковый набор («Прогресс» и «Уровень 3» одним
        /// кеглем) читался как два заголовка страницы.
        static var levelLabel: String { t("Level", "Уровень") }
        static func totalXp(_ value: Int) -> String {
            t("\(value) XP total", "Всего \(value) XP")
        }
        /// Split around the number so it can be animated by `CountUpText`.
        static var totalXpPrefix: String { t("", "Всего ") }
        static var totalXpSuffix: String { t(" XP total", " XP") }
        static func xpToNextLevel(_ remaining: Int, _ level: Int) -> String {
            t(
                "\(remaining) XP to level \(level)",
                "\(remaining) XP до уровня \(level)"
            )
        }
        static var lastSevenDays: String { t("Last 7 days", "Последние 7 дней") }
        static func gateHistory(_ count: Int) -> String {
            t(
                "\(count) gate \(count == 1 ? "attempt" : "attempts")",
                "\(count) \(plural(count, "попытка", "попытки", "попыток")) на гейтах"
            )
        }
        static var blocksPassed: String { t("Blocks passed", "Блоков сдано") }
        static var lessonsRead: String { t("Lessons read", "Уроков пройдено") }
        static var skillsTitle: String { t("Skills", "Навыки") }
        static var skillsSubtitle: String {
            t(
                "One competency per domain of the map, plus communication. Trend is based "
                    + "on your last five gates.",
                "По одной компетенции на домен карты плюс коммуникация. Тренд считается по "
                    + "последним пяти гейтам."
            )
        }
    }

    enum History {
        static var title: String { t("History", "История") }
        static var loadFailed: String {
            t("Couldn't load history", "Не удалось загрузить историю")
        }
        static var emptyTitle: String {
            t("No gates attempted yet", "Гейтов пока не было")
        }
        static var emptyBody: String {
            t(
                "Finish the lessons of a block and take its gate — every sitting shows up here.",
                "Пройдите уроки блока и сдайте его гейт — каждая попытка появится здесь."
            )
        }
        static var passed: String { t("Passed", "Сдан") }
        static var notPassed: String { t("Not passed", "Не сдан") }

        static func blockAndAttempt(_ blockTitle: String, _ index: Int) -> String {
            t(
                "\(blockTitle) · attempt \(index)",
                "\(blockTitle) · попытка \(index)"
            )
        }
        static var loadMore: String { t("Load more", "Показать ещё") }
        static var coachingReady: String { t("Coaching ready", "Разбор готов") }
        static var feedbackPending: String { t("Feedback pending", "Разбор готовится") }
        static var coachingFailed: String { t("Coaching failed", "Разбор не удался") }

        static var resultTitle: String { t("Result", "Результат") }
        static var resultLoadFailed: String {
            t("Couldn't load result", "Не удалось загрузить результат")
        }
        static var pendingXpNote: String {
            t(
                "Your answer is saved. XP is pending until coaching completes.",
                "Ответ сохранён. XP будет начислён после завершения разбора."
            )
        }
    }

    // MARK: - Profile

    enum Profile {
        static var title: String { t("Profile", "Профиль") }
        static var practiceSection: String { t("Your practice", "Ваша практика") }
        static var level: String { t("Level", "Уровень") }
        static var totalXp: String { t("Total XP", "Всего XP") }
        static var targetRole: String { t("Target role", "Целевая роль") }

        static var roleSection: String { t("Role", "Роль") }
        static var roleFooter: String {
            t(
                "A highlight over the map, nothing more: it does not change the order blocks "
                    + "open in or what a gate asks of you.",
                "Это только подсветка на карте: порядок открытия блоков и требования гейта "
                    + "она не меняет."
            )
        }

        static var languageSection: String { t("Language", "Язык") }
        static var languageLabel: String { t("Interface language", "Язык интерфейса") }
        static var languageFooter: String {
            t(
                "Changes everything: the app's own text, scenario briefs and evidence, the "
                    + "consequences, and the coaching you get back. Results you have already "
                    + "finished are shown in the new language too.",
                "Меняет всё: тексты приложения, описания сценариев и данные, последствия и "
                    + "разбор, который вы получаете. Уже завершённые результаты тоже "
                    + "показываются на новом языке."
            )
        }

        static var privacySection: String { t("Privacy", "Приватность") }
        static var privacyNotice: String { t("Privacy notice", "О приватности") }

        static var developerSection: String { t("Developer", "Разработка") }
        static var apply: String { t("Apply", "Применить") }
        static var developerFooter: String {
            t(
                "Point the app at a different API host. Debug builds only. Restart the app "
                    + "after changing this.",
                "Направить приложение на другой API-хост. Только в debug-сборках. После "
                    + "изменения перезапустите приложение."
            )
        }

        static var signOut: String { t("Sign out", "Выйти") }
        static var signOutQuestion: String { t("Sign out?", "Выйти из аккаунта?") }
        static var signOutMessage: String {
            t(
                "Any draft that hasn't synced yet will be cleared from this device.",
                "Черновики, которые ещё не синхронизировались, будут удалены с этого устройства."
            )
        }
        static var deleteAccount: String { t("Delete account", "Удалить аккаунт") }
        static var deleteQuestion: String { t("Delete your account?", "Удалить ваш аккаунт?") }
        static var deletePermanently: String { t("Delete permanently", "Удалить навсегда") }
        static var deleteMessage: String {
            t(
                "This removes your responses, feedback and identity link. It cannot be undone.",
                "Это удалит ваши ответы, разборы и связь с учётной записью. Отменить нельзя."
            )
        }
        static var deleteFooter: String {
            t(
                "Deleting your account removes your written responses, your feedback, and your "
                    + "identity link. This cannot be undone.",
                "Удаление аккаунта убирает ваши письменные ответы, разборы и связь с учётной "
                    + "записью. Отменить это нельзя."
            )
        }
        static var deleting: String { t("Deleting your account…", "Удаляем ваш аккаунт…") }

        static func version(_ version: String, _ build: String) -> String {
            t("Version \(version) (\(build))", "Версия \(version) (\(build))")
        }
    }

    // MARK: - Errors

    enum Errors {
        static var offline: String {
            t(
                "You're offline. Your work is saved on this device and will sync when you "
                    + "reconnect.",
                "Вы офлайн. Работа сохранена на устройстве и синхронизируется при подключении."
            )
        }
        static var timedOut: String {
            t(
                "That took too long. Check your connection and try again.",
                "Это заняло слишком много времени. Проверьте соединение и повторите."
            )
        }
        static var unauthorized: String {
            t(
                "Your session expired. Sign in again to continue.",
                "Сессия истекла. Войдите снова, чтобы продолжить."
            )
        }
        static var notAvailable: String {
            t(
                "That challenge isn't available on this account.",
                "Это задание недоступно для вашего аккаунта."
            )
        }
        static var onboardingIncomplete: String {
            t(
                "Finish setting up your account to see today's challenge.",
                "Завершите настройку аккаунта, чтобы увидеть сегодняшнее задание."
            )
        }
        static var alreadySubmitted: String {
            t(
                "That's already been submitted. Pull to refresh for the latest state.",
                "Это уже отправлено. Потяните вниз, чтобы обновить состояние."
            )
        }
        static var noEvidenceReviewed: String {
            t(
                "Open at least one signal before making a decision.",
                "Откройте хотя бы один сигнал, прежде чем принимать решение."
            )
        }
        static func rationaleLength(_ minimum: Int, _ maximum: Int) -> String {
            t(
                "Your reasoning needs to be between \(minimum) and \(maximum) characters.",
                "Аргументация должна быть от \(minimum) до \(maximum) символов."
            )
        }
        static var invalidSubmission: String {
            t(
                "Something in that submission wasn't valid. Check your answer and try again.",
                "Что-то в отправке оказалось некорректным. Проверьте ответ и повторите."
            )
        }
        static var rateLimited: String {
            t(
                "You've reached today's coaching limit. Try again tomorrow.",
                "Вы исчерпали дневной лимит разборов. Попробуйте завтра."
            )
        }
        static var noScenarioAvailable: String {
            t(
                "Today's challenge isn't ready yet. Try again in a moment.",
                "Сегодняшнее задание ещё не готово. Попробуйте через минуту."
            )
        }
        static var serverProblem: String {
            t(
                "The server had a problem. Your answer is safe — try again shortly.",
                "На сервере возникла проблема. Ваш ответ в безопасности — повторите чуть позже."
            )
        }
        static var unexpectedResponse: String {
            t(
                "Something unexpected came back from the server. Try again shortly.",
                "С сервера пришло что-то неожиданное. Повторите чуть позже."
            )
        }
    }

    // MARK: - Vocabularies the server sends as keys

    enum Labels {

        static func level(_ key: String) -> String {
            switch key {
            case "foundation": return t("Foundation", "Основы")
            case "developing": return t("Developing", "Развитие")
            case "advanced": return t("Advanced", "Продвинутый")
            default: return key.capitalized
            }
        }

        /// Mirrors `SKILL_LABELS` in `server/app/services/skills.py`, keyed the same way.
        static func skill(_ key: String, fallback: String) -> String {
            switch key {
            case "discovery": return t("Discovery & Research", "Дискавери и исследования")
            case "value_design": return t("Value & Solution Design", "Ценность и проектирование")
            case "delivery": return t("Development & Delivery", "Разработка и поставка")
            case "marketing": return t("Product Marketing", "Продуктовый маркетинг")
            case "growth": return t("Growth & Experiments", "Рост и эксперименты")
            case "economics": return t("Sales & Economics", "Продажи и экономика")
            case "communication": return t("Communication", "Коммуникация")
            default: return fallback
            }
        }

        /// Mirrors `score_band` in `server/app/services/scoring.py`. The score itself stays
        /// the server's to compute; this only translates the band it already chose.
        static func band(_ serverBand: String) -> String {
            switch serverBand {
            case "Strong reasoning": return t(serverBand, "Сильная аргументация")
            case "Solid reasoning": return t(serverBand, "Уверенная аргументация")
            case "Developing reasoning": return t(serverBand, "Растущая аргументация")
            case "Early reasoning": return t(serverBand, "Ранняя аргументация")
            case "Needs a fuller argument": return t(serverBand, "Нужна более полная аргументация")
            default: return serverBand
            }
        }

        static func evidenceType(_ key: String) -> String {
            switch key {
            case "quantitative": return t("Data", "Данные")
            case "qualitative": return t("Voices", "Голоса")
            case "technical": return t("Technical", "Технически")
            case "business": return t("Business", "Бизнес")
            default: return key.capitalized
            }
        }

        static func trendDescription(_ trend: String) -> String {
            switch trend {
            case "up": return t("trending up", "растёт")
            case "down": return t("trending down", "снижается")
            default: return t("steady", "без изменений")
            }
        }

        static func skillAccessibility(_ score: Int, _ trend: String) -> String {
            t(
                "\(score) out of 100, \(trendDescription(trend))",
                "\(score) из 100, \(trendDescription(trend))"
            )
        }

        static func activityState(_ state: String) -> String {
            switch state {
            case "completed": return t("completed", "выполнено")
            case "today": return t("today", "сегодня")
            case "upcoming": return t("upcoming", "предстоит")
            default: return t("missed", "пропущено")
            }
        }

        enum Breakdown {
            static var evidence: String { t("Evidence engagement", "Работа с данными") }
            static var decision: String { t("Decision quality", "Качество решения") }
            static var rationale: String { t("Rationale quality", "Качество аргументации") }
            static var communication: String { t("Communication clarity", "Ясность изложения") }
        }

        enum State {
            static var start: String { t("Start", "Начать") }
            static var resume: String { t("Continue", "Продолжить") }
            static var review: String { t("Review", "Пересмотреть") }
            static var continueLater: String { t("Continue later", "Продолжить позже") }
            static var coachingInProgress: String { t("Coaching in progress", "Разбор готовится") }
            static var completed: String { t("Completed", "Выполнено") }
        }
    }

    // MARK: - Practice

    /// Тренировка навыков собеседования. Двуязычен здесь только интерфейс: сами
    /// задачи, ответы и разборы — по-английски, потому что и собеседования на эти
    /// роли проходят по-английски. Тренировать формулировку на одном языке, чтобы
    /// произносить её на другом, смысла нет.
    enum Practice {
        static var title: String { t("Practice", "Практика") }
        static var inPreparation: String { t("In preparation", "Готовится") }
        static var tests: String { t("What it tests", "Что проверяет") }
        static var format: String { t("Format", "Формат") }

        static var newTask: String { t("New task", "Новая задача") }
        static var anotherTask: String { t("Another task", "Другая задача") }
        static var writingTask: String { t("Writing a task…", "Пишем задачу…") }
        static var readingAnswer: String { t("Reading your answer…", "Читаем ваш ответ…") }
        static var submit: String { t("Get feedback", "Получить разбор") }
        static var backToTracks: String { t("All tracks", "Все направления") }

        static var theTask: String { t("The task", "Задача") }
        static var constraints: String { t("Constraints", "Ограничения") }
        static var clarifiers: String { t("Clarifying questions", "Уточняющие вопросы") }
        /// Не спросить — это тоже ответ, и именно это здесь проверяется.
        static var clarifiersHint: String {
            t(
                "Ask before you answer. What you choose to ask is part of what the review reads.",
                "Спрашивайте до ответа: что именно вы спросили, разбор тоже читает."
            )
        }
        static var ask: String { t("Ask", "Спросить") }
        /// Возражение заперто, пока позиция не занята: в этом весь смысл механизма —
        /// отвечать на «а если нет» имеет смысл только тому, кто уже сказал «да».
        static var counterLocked: String {
            t(
                "Fill in the fields above first — the objection comes after you have committed.",
                "Сначала заполните поля выше: возражение приходит после того, как позиция занята."
            )
        }
        static var yourAnswer: String { t("Your answer", "Ваш ответ") }
        static var timeOnTask: String { t("Time on task", "Время над задачей") }

        static func target(_ minutes: Int) -> String {
            t("about \(minutes) min", "около \(minutes) мин")
        }
        static func charactersLeft(_ count: Int) -> String {
            t(
                "\(count) more characters",
                "ещё \(count) \(plural(count, "символ", "символа", "символов"))"
            )
        }
        static func sessionsSaved(_ count: Int) -> String {
            t(
                "\(count) saved",
                "\(count) \(plural(count, "сохранена", "сохранено", "сохранено"))"
            )
        }

        static var feedback: String { t("Feedback", "Разбор") }
        static var byField: String { t("Field by field", "По частям ответа") }
        static var strengths: String { t("What worked", "Что сработало") }
        static var improvements: String { t("What to sharpen", "Что усилить") }
        static var missedQuestion: String {
            t("The question you didn't ask", "Вопрос, который вы не задали")
        }
        static var sharperApproach: String { t("A sharper answer", "Как было бы сильнее") }

        static var saved: String { t("Saved sessions", "Сохранённые тренировки") }
        static var savedHint: String {
            t(
                "The task, your answer and the review stay together, so you can come back to them.",
                "Задача, ваш ответ и разбор хранятся вместе — к ним можно вернуться."
            )
        }
        static var noSessions: String {
            t("Nothing saved here yet.", "Здесь пока ничего нет.")
        }
        static var open: String { t("Open", "Открыть") }
        static var delete: String { t("Delete", "Удалить") }
        static var deleteConfirm: String {
            t("Delete this session for good?", "Удалить эту тренировку насовсем?")
        }
        static var unanswered: String { t("Not answered", "Без ответа") }
        static var reviewed: String { t("Reviewed", "Разобрано") }

        static var limitReached: String {
            t(
                "That is today's practice limit. It resets 24 hours after your first session today.",
                "На сегодня лимит тренировок исчерпан. Он обновится через сутки после первой сегодняшней."
            )
        }
        static var generationFailed: String {
            t(
                "The task couldn't be written. Try again in a moment.",
                "Задачу написать не удалось. Попробуйте через минуту."
            )
        }
        static var feedbackFailed: String {
            t(
                "The review couldn't be written. Your answer is still here — try again.",
                "Разбор не получился. Ответ на месте — попробуйте ещё раз."
            )
        }
        static var notReady: String {
            t("This track is still in preparation.", "Это направление ещё готовится.")
        }
        enum Bar {
            static var below: String { t("Below the bar", "Ниже планки") }
            static var at: String { t("At the bar", "На уровне планки") }
            static var above: String { t("Above the bar", "Выше планки") }
        }
    }
}

/// Russian selects one of three forms from the count; English never needs this helper,
/// so call sites only reach it from inside a `t(_:_:)` Russian branch.
func plural(_ count: Int, _ one: String, _ few: String, _ many: String) -> String {
    let lastTwo = abs(count) % 100
    if (11...14).contains(lastTwo) { return many }
    switch abs(count) % 10 {
    case 1: return one
    case 2...4: return few
    default: return many
    }
}
