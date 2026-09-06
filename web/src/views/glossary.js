/** Глоссарий домена System Design.
 *
 *  ICP — новичок, и в первом же уроке шесть незнакомых слов. Без карточки термина и
 *  этого экрана домен для целевой аудитории нечитаем: это условие работоспособности,
 *  а не украшение. Поиск идёт и по русскому, и по английскому — без английского
 *  человек не найдёт материал вовне.
 */
import { h, fill, debounce } from "../dom.js";
import { icon } from "../icons.js";
import { loadingState, sheet } from "../components.js";
import { S } from "../strings.js";
import { api } from "../api.js";
import { navigate } from "../router.js";
import { breadcrumb } from "./chrome.js";
import { termCard } from "./content.js";

export function glossaryView() {
  const node = h("div.page");
  let terms = null;
  let query = "";

  const list = h("div.stack.s");

  const load = async () => {
    try {
      const response = await api.glossary(query || undefined);
      terms = response.terms;
    } catch {
      terms = [];
    }
    paint();
  };

  const search = debounce(load, 250);

  const paint = () => {
    if (!terms) {
      fill(list, loadingState());
      return;
    }
    if (!terms.length) {
      fill(list, h("p.muted", S.Glossary.empty));
      return;
    }
    fill(
      list,
      terms.map((term) =>
        h(
          "button.rowlink.card.tight",
          { type: "button", onclick: () => open(term) },
          h(
            "span.grow",
            h(
              "span.row",
              h("span.title", { style: { fontWeight: "500" } }, term.term),
              // Отметка «встречал» ставится сама, когда термин попался в уроке.
              term.seen && icon("checkmark.circle.fill", { size: 13, className: "positive" })
            ),
            h("span.caption.tertiary", { style: { display: "block" } }, term.termEn),
            h("span.small.muted", { style: { display: "block" } }, term.definition)
          )
        )
      )
    );
  };

  const open = (term) =>
    sheet(term.term, termCard(term, (lessonId) => navigate(`/lesson/${lessonId}`)));

  fill(
    node,
    breadcrumb(S.Tab.tree),
    h("h1", S.Glossary.title),
    h("input", {
      type: "search",
      placeholder: S.Glossary.searchPrompt,
      "aria-label": S.Glossary.searchPrompt,
      oninput: (event) => {
        query = event.target.value;
        search();
      },
    }),
    list
  );

  paint();
  load();
  return node;
}
