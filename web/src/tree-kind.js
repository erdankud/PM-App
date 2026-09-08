/** Какое из двух деревьев показывать — продукт или System Design.
 *
 *  Выбор живёт в одном месте, потому что его делают на двух экранах: в «Обучении»
 *  и на карте навыков. Две копии разошлись бы на первом же переключении, и человек
 *  учил бы продукт, а карту смотрел системную.
 */
const KEY = "pmcoach.treeKind";

export function treeKind() {
  try {
    return localStorage.getItem(KEY) || "product";
  } catch {
    return "product";
  }
}

export function setTreeKind(kind) {
  try {
    localStorage.setItem(KEY, kind);
  } catch {
    /* приватный режим */
  }
}
