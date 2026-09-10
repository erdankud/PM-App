/** Обучение — главный экран: чем вы заняты сейчас и что осталось до гейта.
 *
 *  Карта навыков переехала в собственный раздел. Она показывает всю профессию
 *  разом — это обзор, за которым приходят раз в неделю. Каждый день нужен другой
 *  ответ: какой урок читать сейчас и сколько ещё до проверки. Смешивать эти два
 *  вопроса на одной поверхности значило продираться через карту к уроку.
 *
 *  Экран не дублирует «Прогресс»: уровень, XP и восемь компетенций живут там.
 *  Здесь — только маршрут.
 */
import { h, fill } from "../dom.js";
import { icon } from "../icons.js";
import { button, progressTrack, loadingState, errorState, infoDialog } from "../components.js";
import { S } from "../strings.js";
import { api } from "../api.js";
import { navigate } from "../router.js";
import { treeKind, setTreeKind } from "../tree-kind.js";

const DOMAIN_KEY = "pmcoach.learnDomain";

/** Блок, с которого стоит продолжить в этом наборе: сперва тот, где гейт уже
 *  открыт, затем начатый, затем первый доступный. Ровно тот же порядок, что был
 *  у рекомендации на карте. */
function suggested(blocks) {
  const open = blocks.filter(
    (block) => block.status !== "locked" && block.status !== "passed" && block.contentStatus === "published"
  );
  return (
    open.find((block) => block.status === "gate_ready") ||
    open.find((block) => block.status === "in_progress") ||
    open[0] ||
    blocks.find((block) => block.status !== "passed") ||
    blocks[0] ||
    null
  );
}

export function learnView() {
  const node = h("div.page");
  // Дерево общее с картой навыков: переключение на одном экране видно на другом.
  let kind = treeKind();
  let tree = null;
  let detail = null;
  let error = null;
  let domainKey = null;
  // Блок можно выбрать руками: рекомендация — отправная точка, а не рельсы.
  let blockId = null;

  const storedDomain = () => {
    try {
      return localStorage.getItem(`${DOMAIN_KEY}.${kind}`);
    } catch {
      return null;
    }
  };

  const rememberDomain = (key) => {
    try {
      // Ключ с деревом: у продукта и System Design свои шесть направлений.
      localStorage.setItem(`${DOMAIN_KEY}.${kind}`, key);
    } catch {
      /* приватный режим */
    }
  };

  const blocksOf = (key) =>
    tree.blocks.filter((block) => block.domainKey === key).sort((a, b) => a.tier - b.tier);

  /** Сколько уроков пройдено по направлению. Считаем по блокам, а не по узлам:
   *  доступность и прогресс живут на блоке. */
  const domainProgress = (key) => {
    const blocks = blocksOf(key);
    const done = blocks.reduce((sum, block) => sum + block.lessonsCompleted, 0);
    const total = blocks.reduce((sum, block) => sum + block.lessonsTotal, 0);
    return {
      blocks,
      done,
      total,
      share: total ? done / total : 0,
      passed: blocks.filter((block) => block.status === "passed").length,
    };
  };

  const currentBlock = () => {
    const blocks = blocksOf(domainKey);
    return blocks.find((block) => block.id === blockId) || suggested(blocks);
  };

  const pickBlock = (id) => {
    if (id === currentBlock()?.id) return;
    blockId = id;
    detail = null;
    render();
    loadBlock();
  };

  const load = async () => {
    try {
      tree = await api.tree(kind);
      // Направление: сохранённое, иначе то, в котором вы дальше всего продвинулись.
      const stored = domainKey || storedDomain();
      const known = tree.domains.some((domain) => domain.key === stored);
      domainKey = known ? stored : suggested(tree.blocks)?.domainKey || tree.domains[0].key;
      error = null;
      render();
      await loadBlock();
    } catch (apiError) {
      error = apiError;
      render();
    }
  };

  const loadBlock = async () => {
    const block = currentBlock();
    if (!block) return;
    try {
      detail = await api.block(block.id);
    } catch {
      // Список уроков — не единственное содержимое экрана: без него остаётся
      // и переключатель направлений, и кнопка «продолжить».
      detail = null;
    }
    render();
  };

  const setKind = (next) => {
    if (next === kind) return;
    kind = next;
    setTreeKind(next);
    tree = null;
    detail = null;
    domainKey = null;
    blockId = null;
    render();
    load();
  };

  const switcher = () =>
    h(
      "div.segmented.glass",
      { role: "group" },
      h(
        `button${kind === "product" ? ".selected" : ""}`,
        { type: "button", onclick: () => setKind("product") },
        S.Trees.product
      ),
      h(
        `button${kind === "system_design" ? ".selected" : ""}`,
        { type: "button", onclick: () => setKind("system_design") },
        S.Trees.systems
      )
    );

  const pickDomain = (key) => {
    if (key === domainKey) return;
    domainKey = key;
    detail = null;
    blockId = null;
    rememberDomain(key);
    render();
    loadBlock();
  };

  const render = () => {
    const header = h("div.page-header", h("h1", S.Tab.learn), switcher());
    if (error && !tree) {
      fill(node, header, errorState(S.Tree.loadFailed, error.userMessage, load));
      return;
    }
    if (!tree) {
      fill(node, header, loadingState(S.Tree.loading));
      return;
    }
    const block = currentBlock();
    fill(
      node,
      header,
      lede(),
      directions(),
      block ? blockStrip(block) : null,
      block ? continuePlate(block) : null,
      block ? blockLessons(block) : null
    );
  };

  /** Абзац под заголовком: что такое шесть направлений и почему они здесь.
   *  Кнопка «Подробнее» намеренно тихая — это сноска, а не действие экрана. */
  const lede = () =>
    h(
      "p.learn-lede",
      h("span", S.Learn.intro(kind)),
      h(
        "button.learn-more",
        { type: "button", onclick: showAbout },
        S.Learn.learnMore
      )
    );

  const showAbout = () =>
    infoDialog(
      S.Learn.aboutTitle(kind),
      [
        h("p.info-lead", S.Learn.aboutLead(kind)),
        h("h3", S.Tree.domainsTitle),
        h(
          "div.info-list",
          tree.domains.map((domain) =>
            h(
              "div.info-row",
              h("span.info-term", domain.title),
              h("span.info-text", S.Learn.domainBlurb(domain.key))
            )
          )
        ),
        h("h3", S.Tree.tiersTitle),
        h(
          "div.info-list",
          tree.tiers.map((tier) =>
            h(
              "div.info-row",
              h("span.info-term", tier.title),
              h(
                "span.info-text",
                h("span", tier.subtitle),
                h("span.info-audience", S.Learn.levelAudience(tier.tier))
              )
            )
          )
        ),
        h("p.info-source", S.Learn.sourceNote(kind)),
      ]
    );

  /** Три блока выбранного направления: видно, из чего оно состоит и где вы в нём.
   *  Нажатие меняет блок, а не только подсвечивает — иначе это картинка. */
  const blockStrip = (current) =>
    h(
      "section.block-strip",
      h("p.caption.tertiary", S.Learn.blocksTitle),
      h(
        "div.block-strip-row",
        blocksOf(domainKey).map((block) => {
          const share = block.lessonsTotal ? block.lessonsCompleted / block.lessonsTotal : 0;
          const done = block.status === "passed";
          return h(
            `button.block-chip${block.id === current.id ? ".current" : ""}${done ? ".done" : ""}`,
            {
              type: "button",
              onclick: () => pickBlock(block.id),
              "aria-current": block.id === current.id ? "true" : null,
            },
            h(
              "span.block-chip-top",
              h("span.block-chip-id", block.id),
              done ? icon("checkmark.circle.fill", { size: 14 }) : null
            ),
            h("span.block-chip-title", block.title),
            h("span.block-chip-bar", h("i", { style: { width: `${share * 100}%` } })),
            h(
              "span.block-chip-meta",
              S.Tree.lessonsProgress(block.lessonsCompleted, block.lessonsTotal)
            )
          );
        })
      )
    );

  /** Переключатель направлений: где вы сейчас, что ещё есть и сколько пройдено
   *  в каждом. Это и навигация, и ответ на «где я», поэтому он идёт первым. */
  const directions = () =>
    h(
      "section.directions",
      // Заголовок здесь не нужен: шесть плиток с названиями направлений
      // объясняют себя быстрее, чем слово над ними.
      h(
        "div.direction-grid",
        tree.domains.map((domain) => {
          const stats = domainProgress(domain.key);
          const selected = domain.key === domainKey;
          const next = suggested(stats.blocks);
          return h(
            `button.direction${selected ? ".selected" : ""}`,
            {
              type: "button",
              onclick: () => pickDomain(domain.key),
              "aria-pressed": selected ? "true" : "false",
            },
            selected && h("span.direction-flag", S.Tree.currentDirection),
            h("span.direction-name", domain.title),
            // Полоса и есть счётчик уроков — её доля считается из них. Раньше
            // рядом стояло ещё и «0/26»: то же самое числом, без единицы, под
            // подписью про блоки, так что два числа в плитке значили разное и
            // не говорили об этом. Осталась полоса, а единица переехала в её имя.
            h("span.direction-bar", {
              role: "img",
              "aria-label": S.Tree.lessonsProgress(stats.done, stats.total),
            }, h("i", { style: { width: `${stats.share * 100}%` } })),
            h(
              "span.direction-meta",
              h("span", S.Tree.blocksProgress(stats.passed, stats.blocks.length))
            ),
            // Название блока, который здесь откроется. Раньше нетронутые
            // направления печатали «Здесь вы ещё не начинали» — одну и ту же
            // фразу пять раз подряд, и ни одна из пяти не говорила, что там.
            h("span.direction-next", next?.title || "")
          );
        })
      )
    );

  /** Чёрная плита: одно действие, на которое рассчитан экран. */
  const continuePlate = (block) => {
    const lesson = nextLesson();
    return h(
      "section.continue-plate",
      h(
        "div.continue-body",
        h("span.continue-kicker", `${S.Tree.continueLesson} · ${block.id} ${block.title}`),
        h("h2.continue-title", lesson ? lesson.title : block.title),
        h(
          "p.continue-meta",
          lesson
            ? `${lesson.nodeTitle} · ${S.Common.minutes(lesson.estimatedMinutes)}`
            : S.Tree.lessonsProgress(block.lessonsCompleted, block.lessonsTotal)
        )
      ),
      h(
        "div.continue-action",
        h("p.continue-meta", S.Tree.lessonsProgress(block.lessonsCompleted, block.lessonsTotal)),
        lesson
          ? button(S.Tree.continueLesson, () => navigate(`/lesson/${lesson.id}`), { arrow: true })
          : button(S.Tree.openBlock, () => navigate(`/block/${block.id}`), { arrow: true })
      )
    );
  };

  /** Первый непрочитанный урок блока — то, что открывает кнопка. */
  const nextLesson = () => {
    if (!detail) return null;
    const flat = detail.nodes.flatMap((entry) =>
      entry.lessons.map((lesson) => ({ ...lesson, nodeTitle: entry.node.title }))
    );
    return flat.find((lesson) => !lesson.completed) || flat[0] || null;
  };

  /** Уроки блока списком, гейт — последней строкой. Раньше человек читал уроки
   *  на одном экране, а сдавал на другом, и связь держалась на памяти. */
  const blockLessons = (block) => {
    if (!detail) return h("section.block-lessons", loadingState());
    const flat = detail.nodes.flatMap((entry) =>
      entry.lessons.map((lesson) => ({ ...lesson, nodeTitle: entry.node.title }))
    );
    const upcoming = flat.find((lesson) => !lesson.completed);
    return h(
      "section.block-lessons",
      h(
        "div.directions-head",
        h("h2", S.Tree.blockLessonsTitle),
        h("p.caption.tertiary", `${block.id} · ${detail.tierTitle}`)
      ),
      h(
        "div.lesson-list",
        flat.map((lesson) =>
          h(
            `button.lesson-row${lesson.completed ? ".done" : ""}${lesson === upcoming ? ".now" : ""}`,
            { type: "button", onclick: () => navigate(`/lesson/${lesson.id}`) },
            h("span.lesson-mark", lesson.completed ? icon("checkmark", { size: 12 }) : null),
            h(
              "span.grow",
              h("span.lesson-node", lesson.nodeTitle),
              h("span.lesson-name", lesson.title)
            ),
            h("span.lesson-min", S.Common.minutes(lesson.estimatedMinutes))
          )
        ),
        gateRow(block)
      )
    );
  };

  const gateRow = (block) => {
    const ready = detail?.gateAvailable;
    return h(
      `button.gate-row${ready ? ".ready" : ""}`,
      {
        type: "button",
        disabled: !ready,
        onclick: () => navigate(`/block/${block.id}`),
      },
      h("span.gate-tag", S.Tree.gateTitle),
      h("span.grow", ready ? S.Tree.gateHeadline : S.Tree.gateLocked),
      ready ? icon("arrow.right", { size: 14 }) : icon("lock", { size: 13 })
    );
  };

  render();
  load();
  return node;
}
