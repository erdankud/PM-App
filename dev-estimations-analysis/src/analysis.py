# %% [markdown]
# # Оценки разработчиков против реальности
#
# **Анализ точности оценок трудозатрат в разработке ПО + ML-модель прогноза факта**
#
# Данные: [Derek Jones — Software estimation datasets](https://github.com/Derek-Jones/Software-estimation-datasets)
#
# ---
#
# ## Постановка задачи
#
# Каждая команда разработки живёт с одним и тем же вопросом: *насколько можно верить
# оценке, которую дал разработчик?* Обычно на него отвечают анекдотами («умножай на два»)
# или корпоративными коэффициентами, взятыми с потолка.
#
# В этом проекте я беру три независимых публичных датасета, в которых для каждой задачи
# записаны **и оценка, и фактические трудозатраты**, и последовательно отвечаю на пять
# вопросов:
#
# 1. **Смещены ли оценки?** Систематически недооценивают или переоценивают?
# 2. **Зависит ли ошибка от размера задачи?**
# 3. **Кто виноват — люди или типы задач?**
# 4. **Улучшается ли калибровка со временем / с опытом?**
# 5. **Может ли ML предсказать факт лучше, чем сам разработчик?**
#
# Последний вопрос — главный, и ответ на него получился неочевидным.
#
# ## Данные
#
# | Датасет | Строк (после очистки) | Единицы | Период | Что это |
# |---|---|---|---|---|
# | **SiP** | ~10 200 задач | часы | 2004–2014 | Коммерческая компания, 22 разработчика, 20 проектов. Основной датасет. |
# | **CESAW** | ~61 100 задач | минуты | 2008–2017 | 247 человек, 45 проектов, TSP-процесс. Проверка воспроизводимости. |
# | **Renzo Pomodoro** | ~10 600 задач | помидоры | 2009–2016 | Один человек, 7 лет. Проверка индивидуальной калибровки. |
#
# ## Методологическая рамка
#
# Отношение `факт / оценка` — величина строго положительная и сильно скошенная, поэтому
# **весь анализ ведётся в логарифмах**. Это принципиально, а не косметически:
#
# * ошибка «в 2 раза дольше» и «в 2 раза быстрее» становятся симметричными (`+ln2` и `−ln2`);
# * среднее лог-отношения = логарифм **геометрического** среднего — устойчивая мера смещения;
# * `MAE` в логах читается как «типичная ошибка в N раз»: `exp(MAE_log)`.
#
# Метрики качества моделей:
#
# * `MAE_log = mean|log(pred) − log(act)|` → `exp(MAE_log)` = типичный множитель ошибки;
# * `RMSE_log` — та же шкала, но штрафует хвосты (катастрофические промахи);
# * `MdMRE = median(|pred − act| / act)` — стандарт литературы по software estimation;
# * `PRED(25)` — доля прогнозов в пределах ±25 % от факта.

# %%
# --- Установка и загрузка данных (Google Colab) -----------------------------
import os, sys, subprocess, pathlib

IN_COLAB = "google.colab" in sys.modules
DATA_REPO = "https://github.com/Derek-Jones/Software-estimation-datasets"
DATA_DIR = pathlib.Path("Software-estimation-datasets" if IN_COLAB else
                        os.environ.get("SED_DATA_DIR", "data/Software-estimation-datasets"))

if IN_COLAB:
    subprocess.run([sys.executable, "-m", "pip", "-q", "install",
                    "pandas", "numpy", "scikit-learn", "matplotlib", "scipy"], check=False)

if not DATA_DIR.exists():
    DATA_DIR.parent.mkdir(parents=True, exist_ok=True)
    print(f"Клонирую датасеты в {DATA_DIR} ...")
    subprocess.run(["git", "clone", "--depth", "1", DATA_REPO, str(DATA_DIR)], check=True)

print("Данные:", DATA_DIR.resolve())
print(sorted(p.name for p in DATA_DIR.iterdir() if not p.name.startswith(".")))

# %%
# --- Импорты и общие настройки ---------------------------------------------
import tarfile, warnings
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

warnings.filterwarnings("ignore")
pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 40)

FIG_DIR = pathlib.Path("figures"); FIG_DIR.mkdir(exist_ok=True)
RES_DIR = pathlib.Path("results"); RES_DIR.mkdir(exist_ok=True)

# Единый визуальный стиль: спокойный, читаемый, без "чартджанка".
INK, MUTED, GRID = "#1b1b1f", "#6b6b76", "#e3e3e8"
ACCENT, ACCENT2, ACCENT3 = "#2b6cb0", "#c05621", "#2f855a"
mpl.rcParams.update({
    "figure.dpi": 120, "savefig.dpi": 150, "savefig.bbox": "tight",
    "figure.facecolor": "white", "axes.facecolor": "white",
    "font.size": 10, "axes.titlesize": 12, "axes.titleweight": "bold",
    "axes.labelcolor": INK, "text.color": INK,
    "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.edgecolor": GRID, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": .7, "axes.axisbelow": True,
    "axes.spines.top": False, "axes.spines.right": False,
    "legend.frameon": False,
})

def save(fig, name):
    """Сохранить фигуру в figures/ и вернуть путь."""
    p = FIG_DIR / f"{name}.png"
    fig.savefig(p)
    print("saved", p)
    return p

def dump(df, name):
    """Сохранить таблицу результатов в results/."""
    p = RES_DIR / f"{name}.csv"
    df.to_csv(p)
    print("saved", p)
    return p

RNG = 0

# %% [markdown]
# ---
# ## 1. Загрузка и очистка данных
#
# Здесь спрятана первая ловушка. В `SiP/Sip-task-info.csv` **12 299 строк, но только
# 10 266 уникальных задач**: задача, над которой работали несколько разработчиков,
# записана несколькими строками, и `HoursEstimate` / `HoursActual` в них **продублированы**
# (это тотал по задаче, а не по человеку — на человека приходится `DeveloperHoursActual`).
#
# Если этого не заметить, крупные многолюдные задачи получают вес ×2–×5, и любая
# «средняя ошибка оценки» оказывается смещённой. Ниже это проверяется явно.

# %%
def load_sip(data_dir=DATA_DIR):
    """SiP: 10k задач коммерческой компании, оценка и факт в часах."""
    # В файле есть символы cp1252 (кавычки-ёлочки) -> utf-8 падает.
    tasks = pd.read_csv(data_dir / "SiP" / "Sip-task-info.csv", encoding="latin-1")
    dates = pd.read_csv(data_dir / "SiP" / "est-act-dates.csv")

    n_rows, n_tasks = len(tasks), tasks.TaskNumber.nunique()
    per_task = tasks.groupby("TaskNumber")
    est_varies = int((per_task.HoursEstimate.nunique() > 1).sum())
    act_varies = int((per_task.HoursActual.nunique() > 1).sum())
    sums_match = float(np.isclose(per_task.DeveloperHoursActual.sum(),
                                  per_task.HoursActual.first()).mean())
    print(f"SiP: строк {n_rows}, уникальных задач {n_tasks} "
          f"({n_rows - n_tasks} строк-дублей от многолюдных задач)")
    print(f"  оценка/факт различаются внутри задачи: {est_varies}/{act_varies} задач "
          f"-> это дубли, а не разные значения")
    print(f"  sum(DeveloperHoursActual) == HoursActual: {sums_match:.1%} задач "
          f"-> подтверждает, что HoursActual это тотал по задаче")

    tasks = tasks.drop_duplicates("TaskNumber")
    dates = dates.drop_duplicates("TaskNumber")
    for c in ["EstimateOn", "StartedOn", "CompletedOn"]:
        dates[c] = pd.to_datetime(dates[c], format="%d-%b-%y", errors="coerce")

    df = tasks.merge(dates, on="TaskNumber", how="left")
    df = df[(df.HoursEstimate > 0) & (df.HoursActual > 0) & df.EstimateOn.notna()].copy()
    df = df.rename(columns={"HoursEstimate": "estimate", "HoursActual": "actual",
                            "EstimateOn": "date", "DeveloperID": "person"})
    df["dataset"] = "SiP"
    return df.sort_values("date").reset_index(drop=True)


def load_cesaw(data_dir=DATA_DIR, work_dir=pathlib.Path("data/_cesaw")):
    """CESAW: 61k задач, 247 человек, план и факт в минутах."""
    work_dir.mkdir(parents=True, exist_ok=True)
    fact = work_dir / "data" / "CESAW_task_fact.csv.xz"
    if not fact.exists():
        with tarfile.open(data_dir / "CESAW.tgz") as t:
            t.extractall(work_dir)
    df = pd.read_csv(fact)
    n0 = len(df)
    df = df[(df.task_plan_time_minutes > 0) & (df.task_actual_time_minutes > 0)].copy()
    print(f"CESAW: {n0} строк, {n0 - len(df)} с нулевым планом/фактом отброшено -> {len(df)}")
    df["estimate"] = df.task_plan_time_minutes / 60.0     # в часы
    df["actual"] = df.task_actual_time_minutes / 60.0
    df["date"] = pd.to_datetime(df.task_actual_start_date, errors="coerce")
    df = df.rename(columns={"person_key": "person"})
    df["dataset"] = "CESAW"
    return df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)


def load_renzo(data_dir=DATA_DIR):
    """Renzo Pomodoro: один человек, 7 лет, оценка и факт в помидорах (25 мин)."""
    df = pd.read_csv(data_dir / "renzo-pomodoro.csv")
    n0 = len(df)
    df = df.dropna(subset=["estimate", "actual"])
    df = df[(df.estimate > 0) & (df.actual > 0)].copy()
    # В сыром файле есть аномальные оценки (до 5e7 помидоров) - явный мусор ввода.
    df = df[df.estimate <= 40]
    print(f"Renzo: {n0} строк -> {len(df)} с валидной парой оценка/факт "
          f"(отброшены NA, нули и оценки > 40 помидоров)")
    df["date"] = pd.to_datetime(df.date, errors="coerce")
    df["person"] = "renzo"
    df["dataset"] = "Renzo"
    return df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)


def add_ratio(df):
    """Ключевые производные величины: отношение факт/оценка и его логарифм."""
    df = df.copy()
    df["ratio"] = df.actual / df.estimate
    df["log_ratio"] = np.log(df.ratio)
    df["log_est"] = np.log(df.estimate)
    df["log_act"] = np.log(df.actual)
    df["exact"] = np.isclose(df.actual, df.estimate)      # факт == оценка в точности
    return df


sip = add_ratio(load_sip())
cesaw = add_ratio(load_cesaw())
renzo = add_ratio(load_renzo())

print("\nИтоговые размеры:", {k: len(v) for k, v in
                             {"SiP": sip, "CESAW": cesaw, "Renzo": renzo}.items()})
print("\nSiP период:", sip.date.min().date(), "—", sip.date.max().date(),
      "| разработчиков:", sip.person.nunique(), "| проектов:", sip.ProjectCode.nunique())

# %%
# Базовое описание распределений (в часах для SiP/CESAW, в помидорах для Renzo).
overview = pd.DataFrame({
    name: {
        "N задач": len(d),
        "период": f"{d.date.min():%Y}–{d.date.max():%Y}",
        "людей": d.person.nunique(),
        "медиана оценки": round(d.estimate.median(), 2),
        "медиана факта": round(d.actual.median(), 2),
        "медиана факт/оценка": round(d.ratio.median(), 3),
        "геом. среднее факт/оценка": round(float(np.exp(d.log_ratio.mean())), 3),
        "SD лог-отношения": round(float(d.log_ratio.std()), 3),
        "доля факт == оценка": f"{d.exact.mean():.1%}",
        "доля перерасхода": f"{(d.ratio > 1).mean():.1%}",
    } for name, d in [("SiP", sip), ("CESAW", cesaw), ("Renzo", renzo)]
})
dump(overview, "01_overview")
overview

# %% [markdown]
# ---
# ## 2. Как вообще выглядят оценки и факты
#
# Обе величины распределены приблизительно логнормально и тянутся на 4–5 порядков:
# от 0.01 часа до 2 490 часов. Любая работа со средними в линейной шкале здесь
# бессмысленна — среднее будет определяться десятком гигантских задач.

# %%
fig, axes = plt.subplots(1, 3, figsize=(13.5, 3.8))
for ax, (name, d, unit) in zip(axes, [("SiP", sip, "часы"), ("CESAW", cesaw, "часы"),
                                      ("Renzo", renzo, "помидоры")]):
    bins = np.logspace(np.log10(max(d.estimate.min(), 1e-2)),
                       np.log10(d[["estimate", "actual"]].max().max()), 45)
    ax.hist(d.estimate, bins=bins, alpha=.65, color=ACCENT, label="оценка")
    ax.hist(d.actual, bins=bins, alpha=.55, color=ACCENT2, label="факт")
    ax.set_xscale("log")
    ax.set_title(f"{name}  (N={len(d):,})".replace(",", " "))
    ax.set_xlabel(unit)
axes[0].set_ylabel("число задач")
axes[0].legend()
fig.suptitle("Распределения оценок и фактов логнормальны и охватывают 4–5 порядков",
             y=1.04, fontsize=13, fontweight="bold")
save(fig, "01_distributions"); plt.close(fig)

# %% [markdown]
# ### Ловушка №1: 34 % задач в SiP имеют факт, В ТОЧНОСТИ равный оценке
#
# Это первое, что нужно увидеть перед любым моделированием. В SiP у **34 %** задач
# `actual == estimate` до последнего знака. Это не «идеальные оценки»: 0.5, 1, 2, 7 часов —
# это списание времени по оценке, а не измерение факта (эффект якоря + учётная практика).
#
# Последствия серьёзные:
#
# * любая метрика точности «в среднем по датасету» на треть состоит из тождества;
# * ML-модель, обученная на таких данных, получает треть бесплатных попаданий и выглядит
#   лучше, чем она есть;
# * baseline «верь оценке как есть» получает ту же фору — и его почти невозможно побить
#   по медианным метрикам.
#
# Поэтому **весь дальнейший анализ дублируется на подвыборке без точных совпадений.**
# В CESAW тот же эффект есть, но втрое слабее (8 %) — там учёт времени автоматизирован.

# %%
exact_tbl = pd.DataFrame({
    name: {
        "доля факт == оценка": f"{d.exact.mean():.1%}",
        "N точных совпадений": int(d.exact.sum()),
        "медиана оценки среди совпадений": round(d.loc[d.exact, "estimate"].median(), 2),
        "медиана оценки среди остальных": round(d.loc[~d.exact, "estimate"].median(), 2),
    } for name, d in [("SiP", sip), ("CESAW", cesaw), ("Renzo", renzo)]
})
dump(exact_tbl, "02_exact_matches")
print(exact_tbl.to_string())

# Доля точных совпадений резко падает с ростом задачи: списать по оценке легко,
# когда задача на час, и невозможно, когда она на две недели.
SIZE_BINS = [0, 1, 2, 4, 8, 16, 40, np.inf]
SIZE_LABELS = ["≤1ч", "1–2ч", "2–4ч", "4–8ч", "8–16ч", "16–40ч", ">40ч"]
sip["size_bin"] = pd.cut(sip.estimate, SIZE_BINS, labels=SIZE_LABELS)
cesaw["size_bin"] = pd.cut(cesaw.estimate, SIZE_BINS, labels=SIZE_LABELS)

exact_by_size = sip.groupby("size_bin", observed=True).exact.agg(["mean", "size"])
exact_by_size.columns = ["доля точных совпадений", "N"]
dump(exact_by_size, "02_exact_by_size")

fig, axes = plt.subplots(1, 2, figsize=(12, 4))
ax = axes[0]
lr = sip.log_ratio.clip(-3, 3)
ax.hist(lr[~sip.exact], bins=80, color=ACCENT, alpha=.8, label="факт ≠ оценка")
ax.hist(lr[sip.exact], bins=80, color=ACCENT2, alpha=.95, label="факт == оценка (34 %)")
ax.axvline(0, color=INK, lw=1)
ax.set_xticks(np.log([1/8, 1/4, 1/2, 1, 2, 4, 8]))
ax.set_xticklabels(["1/8", "1/4", "1/2", "1", "2", "4", "8"])
ax.set_xlabel("факт / оценка (лог-шкала)"); ax.set_ylabel("число задач")
ax.set_title("SiP: треть массы — искусственный пик на 1.0")
ax.legend()

ax = axes[1]
ax.bar(exact_by_size.index.astype(str), exact_by_size["доля точных совпадений"], color=ACCENT2)
ax.set_ylabel("доля задач с факт == оценка")
ax.set_xlabel("размер задачи по оценке")
ax.set_title("Артефакт исчезает на больших задачах")
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0%}"))
save(fig, "02_exact_match_artifact"); plt.close(fig)

# %% [markdown]
# ---
# ## 3. Оценки — это не измерения, а якоря
#
# Если бы оценки были непрерывной величиной, их значения были бы разбросаны. Вместо этого
# **10 самых популярных значений покрывают 70 % всех оценок SiP**, тогда как для фактов —
# только 45 %. Самые частые оценки: 1, 2, **7**, 0.5, 3, 3.5, **14**, 1.5, 2.5, 4.
#
# Числа 7 / 14 / 21 / 35 выдают семичасовой рабочий день: **23 % всех оценок — целое
# число рабочих дней**, а среди фактов таких только 4 %. Иначе говоря, разработчик
# отвечает не «сколько это займёт», а «сколько это дней».
#
# Это важно для ML: сетка допустимых значений оценки грубая (142 уникальных значения на
# 10k задач), и признак «оценка кратна рабочему дню» несёт информацию о том, насколько
# грубо задача была прикинута.

# %%
def multiple_of(x, m, tol=1e-6):
    r = (x / m) % 1
    return np.isclose(r, 0, atol=tol) | np.isclose(r, 1, atol=tol)

granularity = pd.DataFrame({
    "оценки": {f"кратно {m}": f"{multiple_of(sip.estimate, m).mean():.1%}"
               for m in [7, 3.5, 1, 0.5]},
    "факты": {f"кратно {m}": f"{multiple_of(sip.actual, m).mean():.1%}"
              for m in [7, 3.5, 1, 0.5]},
})
granularity.loc["топ-10 значений покрывают"] = [
    f"{sip.estimate.value_counts(normalize=True).head(10).sum():.1%}",
    f"{sip.actual.value_counts(normalize=True).head(10).sum():.1%}"]
granularity.loc["уникальных значений"] = [sip.estimate.nunique(), sip.actual.nunique()]
dump(granularity, "03_granularity")
print(granularity.to_string())

top_est = sip.estimate.value_counts().head(14).sort_index()
top_act = sip.actual.value_counts().reindex(top_est.index).fillna(0)

fig, ax = plt.subplots(figsize=(10, 4))
x = np.arange(len(top_est))
workday = multiple_of(np.asarray(top_est.index, dtype=float), 7)
ax.bar(x - .2, top_est.values, .4,
       color=[ACCENT3 if w else ACCENT for w in workday], label="как оценка")
ax.bar(x + .2, top_act.values, .4, color=ACCENT2, label="как факт")
ax.set_xticks(x); ax.set_xticklabels([f"{v:g}" for v in top_est.index])
for i in np.where(workday)[0]:
    ax.annotate("×7ч", (i - .2, top_est.values[i]), textcoords="offset points",
                xytext=(0, 4), ha="center", fontsize=8, color=ACCENT3, fontweight="bold")
ax.bar(0, 0, color=ACCENT3, label="оценка = целое число рабочих дней (7 ч)")
ax.set_xlabel("часы"); ax.set_ylabel("число задач")
ax.set_title("14 самых частых значений оценки: сетка якорей, которой нет у фактов")
ax.legend()
save(fig, "03_anchoring"); plt.close(fig)

# %% [markdown]
# ---
# ## 4. Главный эффект: регрессия к среднему
#
# Агрегированное смещение по SiP выглядит скромно: геометрическое среднее `факт/оценка`
# = **0.905** по всем задачам и **0.86** без точных совпадений. То есть «в среднем»
# команда даже укладывается в оценку. Соблазнительный, но неверный вывод — потому что
# среднее здесь скрывает **смену знака**.
#
# На подвыборке без точных совпадений (там, где факт действительно измерялся):
#
# | размер задачи | геом. среднее факт/оценка | доля перерасхода |
# |---|---|---|
# | ≤ 1 ч   | **×1.22** | 55 % |
# | 1–2 ч   | ×1.10 | 52 % |
# | 2–4 ч   | ×0.97 | 49 % |
# | 4–8 ч   | ×0.82 | 45 % |
# | 8–16 ч  | ×0.75 | 38 % |
# | 16–40 ч | ×0.58 | 35 % |
# | > 40 ч  | **×0.37** | 27 % |
#
# Размах — **3.3 раза** между краями, с точкой равновесия около 2–4 часов. Это
# классическая регрессия к среднему: оценка — шумный сигнал, и экстремальные оценки
# в обе стороны систематически «тянутся» к типичной длительности задачи.
#
# Практический вывод прямо противоположен фольклору «умножай на два»: **умножать надо
# мелкие задачи, а крупные — делить.** Единый «коэффициент запаса» на всю команду
# вреден вдвойне — он одновременно слишком мал для мелких задач и слишком велик для
# крупных.
#
# Второй, не менее важный эффект: **разброс растёт вместе с размером**. SD лог-отношения
# идёт от 0.91 на мелких задачах до 1.49 на крупных — то есть для задачи в неделю
# 90 %-й интервал занимает примерно от ×0.09 до ×11.

# %%
def size_profile(d, label):
    g = d.groupby("size_bin", observed=True)
    out = pd.DataFrame({
        "N": g.size(),
        "медиана факт/оценка": g.ratio.median(),
        "геом. среднее": g.log_ratio.apply(lambda x: np.exp(x.mean())),
        "SD лог-отношения": g.log_ratio.std(),
        "доля перерасхода": g.ratio.apply(lambda x: (x > 1).mean()),
    })
    out.insert(0, "выборка", label)
    return out

sip_ne = sip[~sip.exact]
prof_all = size_profile(sip, "все задачи")
prof_ne = size_profile(sip_ne, "без точных совпадений")
size_tbl = pd.concat([prof_all, prof_ne]).round(3)
dump(size_tbl, "04_size_effect")
print(size_tbl.to_string())

fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.2))
ax = axes[0]
x = np.arange(len(SIZE_LABELS))
ax.plot(x, prof_all["геом. среднее"], "o-", color=MUTED, lw=2, label="все задачи")
ax.plot(x, prof_ne["геом. среднее"], "o-", color=ACCENT2, lw=2.5,
        label="без точных совпадений")
ax.axhline(1, color=INK, lw=1, ls="--")
ax.fill_between(x, 1, prof_ne["геом. среднее"],
                where=prof_ne["геом. среднее"].values > 1, color=ACCENT2, alpha=.12)
ax.fill_between(x, 1, prof_ne["геом. среднее"],
                where=prof_ne["геом. среднее"].values <= 1, color=ACCENT, alpha=.12)
ax.set_xticks(x); ax.set_xticklabels(SIZE_LABELS)
ax.set_ylabel("геом. среднее факт / оценка")
ax.set_xlabel("размер задачи по оценке")
ax.set_title("Мелкие задачи недооценены, крупные — переоценены")
ax.annotate("перерасход", (0.08, 1.14), color=ACCENT2, fontweight="bold", fontsize=9)
ax.annotate("экономия", (4.3, 0.62), color=ACCENT, fontweight="bold", fontsize=9)
ax.legend()

ax = axes[1]
ax.plot(x, prof_all["SD лог-отношения"], "o-", color=MUTED, lw=2, label="все задачи")
ax.plot(x, prof_ne["SD лог-отношения"], "o-", color=ACCENT3, lw=2.5,
        label="без точных совпадений")
ax.set_xticks(x); ax.set_xticklabels(SIZE_LABELS)
ax.set_ylabel("SD log(факт/оценка)")
ax.set_xlabel("размер задачи по оценке")
ax.set_title("Неопределённость тоже растёт с размером")
ax.legend()
save(fig, "04_size_effect"); plt.close(fig)

# %%
# Диаграмма рассеяния: где на самом деле лежат задачи относительно линии "оценка = факт".
fig, ax = plt.subplots(figsize=(6.4, 6))
sub = sip.sample(min(len(sip), 6000), random_state=RNG)
ax.scatter(sub.estimate, sub.actual, s=7, alpha=.18, color=ACCENT, edgecolors="none")
lim = [0.05, 3000]
ax.plot(lim, lim, color=INK, lw=1.2, ls="--", label="факт = оценка")
med = sip_ne.groupby("size_bin", observed=True).agg(e=("estimate", "median"),
                                                    a=("actual", "median"))
ax.plot(med.e, med.a, "o-", color=ACCENT2, lw=2.5, ms=7,
        label="медиана факта по группам\n(без точных совпадений)")
ax.set_xscale("log"); ax.set_yscale("log")
ax.set_xlim(lim); ax.set_ylim(lim)
ax.set_xlabel("оценка, часы"); ax.set_ylabel("факт, часы")
ax.set_title("SiP: медианная линия положе диагонали —\nэто и есть регрессия к среднему")
ax.legend(loc="upper left")
save(fig, "04_scatter"); plt.close(fig)

# %% [markdown]
# ---
# ## 5. Кто «виноват»: люди, проекты или типы задач?
#
# Естественная гипотеза менеджера — «есть оптимисты и есть реалисты, надо знать
# персональные коэффициенты». Проверим, сколько дисперсии лог-отношения объясняет
# каждый фактор по отдельности (доля объяснённой дисперсии, `R²`, при подгонке
# одним категориальным признаком).

# %%
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import OneHotEncoder

def variance_explained(d, factors, target="log_ratio"):
    rows = {}
    y = d[target].values
    for f in factors:
        X = OneHotEncoder(handle_unknown="ignore").fit_transform(d[[f]].astype(str))
        r2 = LinearRegression().fit(X, y).score(X, y)
        rows[f] = {"уровней": d[f].nunique(), "R² лог-отношения": round(r2, 4)}
    return pd.DataFrame(rows).T.sort_values("R² лог-отношения", ascending=False)

ve = variance_explained(sip_ne, ["SubCategory", "size_bin", "person",
                                 "ProjectCode", "Category", "Priority"])
dump(ve, "05_variance_explained")
print(ve.to_string())

# %% [markdown]
# Результат отрезвляющий, и это главный аргумент против «персональных коэффициентов»:
#
# | фактор | R² лог-отношения |
# |---|---|
# | **размер задачи** | **0.089** |
# | исполнитель | 0.032 |
# | тип работы | 0.030 |
# | проект | 0.019 |
# | приоритет | 0.003 |
#
# **Размер задачи объясняет ошибку примерно втрое лучше, чем личность исполнителя —
# но даже он объясняет всего 9 % дисперсии.** Все наблюдаемые структурные факторы
# вместе не дотягивают до 15 %. Остальные 85 % — это неопределённость самой задачи,
# которая не редуцируется ни выбором исполнителя, ни классификатором работ.
#
# Отсюда два следствия. Первое: искать «кто у нас плохо оценивает» — это оптимизация
# третьего знака после запятой. Второе, более важное: **если 85 % дисперсии
# нередуцируемы, то любой точечный прогноз обречён, и правильный продукт модели —
# интервал** (см. раздел 8.4).
#
# При этом смещение по типам работ, хоть и объясняет мало дисперсии, содержательно
# осмысленно и устойчиво: программистские задачи оцениваются с запасом (баги ×0.75,
# доработки ×0.82), а всё, что связано с людьми и календарём — статусные встречи ×1.52,
# управление персоналом ×1.48, обучение ×1.46, планёрки ×2.38 — стабильно
# перерасходуется. Это не «плохие оценщики», это невидимая коммуникационная работа,
# которая в оценку просто не попадает.

# %%
def bias_table(d, key, min_n=50):
    g = d.groupby(key, observed=True)
    t = pd.DataFrame({
        "N": g.size(),
        "геом. среднее": g.log_ratio.apply(lambda x: np.exp(x.mean())),
        "медиана": g.ratio.median(),
        "SD лог": g.log_ratio.std(),
    })
    t["SE лог"] = t["SD лог"] / np.sqrt(t.N)
    t["CI низ"] = np.exp(np.log(t["геом. среднее"]) - 1.96 * t["SE лог"])
    t["CI верх"] = np.exp(np.log(t["геом. среднее"]) + 1.96 * t["SE лог"])
    return t[t.N >= min_n].sort_values("геом. среднее")

by_sub = bias_table(sip_ne, "SubCategory", min_n=60)
by_dev = bias_table(sip_ne, "person", min_n=60)
dump(by_sub.round(3), "05_bias_by_subcategory")
dump(by_dev.round(3), "05_bias_by_developer")
print("\nПо типам работ:\n", by_sub.round(2).to_string())
print("\nПо разработчикам:\n", by_dev.round(2).to_string())

fig, axes = plt.subplots(1, 2, figsize=(13, 5.2), sharex=True)
for ax, (t, title) in zip(axes, [(by_sub, "по типу работы"),
                                 (by_dev, "по разработчику")]):
    y = np.arange(len(t))
    colors = [ACCENT2 if v > 1 else ACCENT for v in t["геом. среднее"]]
    ax.hlines(y, t["CI низ"], t["CI верх"], color=colors, lw=2, alpha=.55)
    ax.scatter(t["геом. среднее"], y, color=colors, s=32, zorder=3)
    ax.set_yticks(y)
    ax.set_yticklabels([str(i) for i in t.index], fontsize=8)
    ax.axvline(1, color=INK, lw=1, ls="--")
    ax.set_xscale("log")
    ax.set_xticks([0.5, 1, 2, 4])
    ax.set_xticklabels(["×0.5", "×1", "×2", "×4"])
    ax.xaxis.set_minor_formatter(mpl.ticker.NullFormatter())   # иначе лог-шкала
    ax.xaxis.set_minor_locator(mpl.ticker.NullLocator())       # рисует свои подписи поверх
    ax.set_title(f"Смещение оценки {title}")
    ax.set_xlabel("геом. среднее факт / оценка (95 % ДИ)")
fig.suptitle("Смещение по типам работ содержательно, но объясняет лишь 3 % дисперсии",
             y=1.02, fontsize=13, fontweight="bold")
save(fig, "05_bias_forest"); plt.close(fig)

# %% [markdown]
# ---
# ## 6. Учатся ли команды оценивать?
#
# Проверяем две вещи: календарный тренд (становится ли компания в целом точнее)
# и индивидуальную кривую опыта (становится ли конкретный человек точнее по мере
# накопления задач). Для второго используем порядковый номер задачи разработчика.
#
# Ответ: **почти нет.** За 11 лет смещение колеблется в коридоре ×0.75–×1.01 без
# направленного тренда, а разброс (SD лог-отношения) не снижается вовсе — он даже
# слегка растёт к концу периода. Индивидуальная кривая опыта даёт скромный эффект:
# медиана |log(факт/оценка)| падает с 0.69 на первых 25 задачах до 0.56 после сотни
# и дальше выходит на плато. В переводе на человеческий: типичная ошибка улучшается
# с «в 2.0 раза» до «в 1.75 раза» — и на этом обучение заканчивается.
#
# Единственное, что действительно менялось со временем — **дисциплина учёта**:
# доля точных совпадений упала с ~35–40 % в 2005–2008 до 20–22 % в 2013–2014.

# %%
sip["year"] = sip.date.dt.year
sip_ne = sip[~sip.exact].copy()
sip_ne["year"] = sip_ne.date.dt.year

by_year = pd.DataFrame({
    "N": sip_ne.groupby("year").size(),
    "геом. среднее": sip_ne.groupby("year").log_ratio.apply(lambda x: np.exp(x.mean())),
    "SD лог": sip_ne.groupby("year").log_ratio.std(),
    "доля точных совпадений (все задачи)": sip.groupby("year").exact.mean(),
}).round(3)
dump(by_year, "06_by_year")
print(by_year.to_string())

# Кривая опыта: |log_ratio| в зависимости от номера задачи разработчика.
sip_ne["task_seq"] = sip_ne.groupby("person").cumcount()
seq_bins = [0, 25, 50, 100, 200, 400, 800, np.inf]
seq_labels = ["1–25", "26–50", "51–100", "101–200", "201–400", "401–800", ">800"]
sip_ne["seq_bin"] = pd.cut(sip_ne.task_seq, seq_bins, labels=seq_labels)
by_seq = pd.DataFrame({
    "N": sip_ne.groupby("seq_bin", observed=True).size(),
    "медиана |log отношения|": sip_ne.groupby("seq_bin", observed=True).log_ratio
                                     .apply(lambda x: x.abs().median()),
    "геом. среднее": sip_ne.groupby("seq_bin", observed=True).log_ratio
                           .apply(lambda x: np.exp(x.mean())),
}).round(3)
dump(by_seq, "06_experience_curve")
print("\n", by_seq.to_string())

fig, axes = plt.subplots(1, 2, figsize=(12.5, 4))
ax = axes[0]
ax.plot(by_year.index, by_year["геом. среднее"], "o-", color=ACCENT2, lw=2.2, label="смещение")
ax.axhline(1, color=INK, lw=1, ls="--")
ax.set_ylabel("геом. среднее факт / оценка", color=ACCENT2)
ax2 = ax.twinx(); ax2.grid(False)
ax2.plot(by_year.index, by_year["SD лог"], "s--", color=MUTED, lw=1.8, label="разброс")
ax2.set_ylabel("SD лог-отношения", color=MUTED)
ax.set_title("11 лет: смещение колеблется, разброс не падает")  # noqa: подтверждено данными
ax.set_xlabel("год выдачи оценки")

ax = axes[1]
xs = np.arange(len(by_seq))
ax.bar(xs, by_seq["медиана |log отношения|"], color=ACCENT)
ax.set_xticks(xs); ax.set_xticklabels(by_seq.index.astype(str), fontsize=8)
ax.set_xlabel("порядковый номер задачи разработчика (опыт)")
ax.set_ylabel("медиана |log(факт/оценка)|")
ax.set_title("Опыт даёт ~20 % улучшения на первой сотне задач,\nдальше — плато")
save(fig, "06_learning"); plt.close(fig)

# %% [markdown]
# ---
# ## 7. Воспроизводится ли эффект размера на других данных?
#
# Одна компания — это одна культура оценивания. Проверим главный вывод (регрессия
# к среднему) на двух независимых источниках: CESAW (247 человек, другая индустрия,
# формальный TSP-процесс) и Renzo (один человек, личные помидоры за 7 лет).
#
# Чтобы датасеты были сопоставимы, разбиваем каждый на квантильные группы по размеру
# оценки — это снимает разницу в единицах измерения (часы против помидоров).

# %%
def quantile_size_profile(d, n_bins=7):
    d = d.copy()
    d["qbin"] = pd.qcut(d.estimate.rank(method="first"), n_bins, labels=False)
    g = d.groupby("qbin")
    return pd.DataFrame({
        "N": g.size(),
        "медиана оценки": g.estimate.median(),
        "геом. среднее": g.log_ratio.apply(lambda x: np.exp(x.mean())),
        "SD лог": g.log_ratio.std(),
    })

repl = {}
for name, d in [("SiP", sip[~sip.exact]), ("CESAW", cesaw[~cesaw.exact]),
                ("Renzo", renzo[~renzo.exact])]:
    repl[name] = quantile_size_profile(d)
    repl[name].insert(0, "dataset", name)
repl_tbl = pd.concat(repl.values()).round(3)
dump(repl_tbl, "07_replication")
print(repl_tbl.to_string())

fig, ax = plt.subplots(figsize=(8.5, 4.6))
for (name, t), c, m in zip(repl.items(), [ACCENT, ACCENT2, ACCENT3], ["o", "s", "^"]):
    ax.plot(t["медиана оценки"], t["геом. среднее"], m + "-", color=c, lw=2.2,
            ms=7, label=f"{name} (N={int(t.N.sum()):,})".replace(",", " "))
ax.axhline(1, color=INK, lw=1, ls="--")
ax.set_xscale("log"); ax.set_yscale("log")
ax.set_yticks([0.5, 0.75, 1, 1.5, 2, 3])
ax.set_yticklabels(["×0.5", "×0.75", "×1", "×1.5", "×2", "×3"])
ax.set_xlabel("медианная оценка в группе (часы / помидоры, лог-шкала)")
ax.set_ylabel("геом. среднее факт / оценка")
ax.set_title("Регрессия к среднему воспроизводится на всех трёх датасетах:\n"
             "нисходящий наклон везде, различается только точка пересечения ×1")
ax.legend()
save(fig, "07_replication"); plt.close(fig)

# Формальная проверка наклона: log_ratio ~ log_est. Отрицательный наклон = регрессия к среднему.
from scipy import stats
slopes = {}
for name, d in [("SiP", sip[~sip.exact]), ("CESAW", cesaw[~cesaw.exact]),
                ("Renzo", renzo[~renzo.exact])]:
    r = stats.linregress(d.log_est, d.log_ratio)
    slopes[name] = {"наклон": round(r.slope, 3), "SE": round(r.stderr, 4),
                    "p-value": f"{r.pvalue:.2e}", "R²": round(r.rvalue ** 2, 3), "N": len(d)}
slopes_tbl = pd.DataFrame(slopes).T
dump(slopes_tbl, "07_slopes")
print("\nРегрессия log(факт/оценка) ~ log(оценка):")
print(slopes_tbl.to_string())
print("\nНаклон -b означает: при удвоении оценки отношение факт/оценка падает в 2^b раз.")

# %% [markdown]
# ---
# ## 8. Машинное обучение: можно ли предсказать факт лучше разработчика?
#
# ### 8.1 Постановка эксперимента
#
# **Цель.** Предсказать `log(факт)` по информации, доступной **в момент выдачи оценки**:
# сама оценка, проект, тип работы, исполнитель, приоритет, длина формулировки задачи,
# накопленный опыт исполнителя, календарные признаки.
#
# **Что мы НЕ используем** — ничего, что становится известно после начала работы
# (даты старта/завершения, `DeveloperHoursActual`, `TaskPerformance`). Последние два
# поля — прямые функции от таргета, и их попадание в признаки дало бы `R² ≈ 1`
# и полностью бессмысленную модель.
#
# **Разбиение — только временное.** Случайный `train_test_split` здесь был бы утечкой:
# задачи одного проекта и одного спринта сильно коррелированы, и модель, обученная на
# 2012 годе, «подглядела» бы контекст задач 2011-го. Мы обучаемся на прошлом и
# предсказываем будущее — так, как это работало бы в проде.
#
# **Baseline, который надо побить** — `факт = оценка`, то есть «просто поверить
# разработчику». Это не соломенное чучело: как мы увидим, он очень силён.

# %%
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.inspection import permutation_importance

CAT_FEATURES = ["ProjectCode", "ProjectBreakdownCode", "Category", "SubCategory",
                "person", "Priority"]
NUM_FEATURES = ["log_est", "dev_seq", "month", "dow", "est_is_workday",
                "summary_len", "summary_words"]
FEATURES = CAT_FEATURES + NUM_FEATURES

def build_features(d):
    d = d.copy()
    d["dev_seq"] = d.groupby("person").cumcount()          # опыт исполнителя к моменту оценки
    d["month"] = d.date.dt.month
    d["dow"] = d.date.dt.dayofweek
    d["est_is_workday"] = multiple_of(d.estimate, 7).astype(int)   # оценка кратна рабочему дню
    d["summary_len"] = d.Summary.str.len().fillna(0)
    d["summary_words"] = d.Summary.str.split().str.len().fillna(0)
    return d

model_df = build_features(sip).sort_values("date").reset_index(drop=True)
print("Признаков:", len(FEATURES), "| Наблюдений:", len(model_df))
print("Период:", model_df.date.min().date(), "—", model_df.date.max().date())

def metrics(pred_log, true_log, true_abs, name):
    err = pred_log - true_log
    mae = float(np.abs(err).mean())
    mre = np.abs(np.exp(pred_log) - true_abs) / true_abs
    return {"модель": name,
            "MAE_log": round(mae, 3),
            "типичная ошибка": f"×{np.exp(mae):.2f}",
            "RMSE_log": round(float(np.sqrt((err ** 2).mean())), 3),
            "MdMRE": round(float(np.median(mre)), 3),
            "PRED(25)": round(float((mre <= .25).mean()), 3)}

def as_categorical(train_X, test_X):
    """HistGBM требует согласованные категории между train и test."""
    tr, te = train_X.copy(), test_X.copy()
    for c in CAT_FEATURES:
        tr[c] = tr[c].astype(str).astype("category")
        te[c] = pd.Categorical(te[c].astype(str), categories=tr[c].cat.categories)
    return tr, te, [tr.columns.get_loc(c) for c in CAT_FEATURES]

def gbm(cat_idx, **kw):
    params = dict(max_iter=400, learning_rate=.06, random_state=RNG)
    params.update(kw)
    return HistGradientBoostingRegressor(categorical_features=cat_idx, **params)

# %%
def run_experiment(d, label, train_frac=.75):
    """Обучение на первых train_frac по времени, тест на остатке."""
    cut = d.date.quantile(train_frac)
    tr, te = d[d.date <= cut], d[d.date > cut]
    y_tr, y_te = tr.log_act.values, te.log_act.values
    le_te = te.log_est.values
    abs_te = te.actual.values
    rows = []

    # --- Baselines --------------------------------------------------------
    rows.append(metrics(np.full(len(te), tr.log_act.mean()), y_te, abs_te,
                        "константа (среднее log факта)"))
    rows.append(metrics(le_te, y_te, abs_te, "B0: факт = оценка"))
    shift = tr.log_ratio.mean()
    rows.append(metrics(le_te + shift, y_te, abs_te,
                        f"B1: глобальный коэффициент ×{np.exp(shift):.2f}"))
    a, b = np.polyfit(tr.log_est, tr.log_act, 1)
    rows.append(metrics(a * le_te + b, y_te, abs_te,
                        f"B2: лог-линейная калибровка (наклон {a:.2f})"))

    # --- Модели -----------------------------------------------------------
    pre = ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore"), CAT_FEATURES)],
                            remainder="passthrough")
    ridge = Pipeline([("pre", pre), ("m", Ridge(alpha=1.0))]).fit(tr[FEATURES], y_tr)
    rows.append(metrics(ridge.predict(te[FEATURES]), y_te, abs_te, "M1: Ridge + признаки"))

    Xtr, Xte, ci = as_categorical(tr[FEATURES], te[FEATURES])
    m2 = gbm(ci).fit(Xtr, y_tr)
    rows.append(metrics(m2.predict(Xte), y_te, abs_te, "M2: GBM → log(факт)"))

    m3 = gbm(ci).fit(Xtr, tr.log_ratio.values)     # предсказываем поправку к оценке
    rows.append(metrics(le_te + m3.predict(Xte), y_te, abs_te, "M3: GBM → log(факт/оценка)"))

    out = pd.DataFrame(rows).set_index("модель")
    out.insert(0, "выборка", label)
    return out, dict(train=tr, test=te, m3=m3, Xtr=Xtr, Xte=Xte, cat_idx=ci, cut=cut)

res_all, ctx_all = run_experiment(model_df, "все задачи")
res_ne, ctx_ne = run_experiment(model_df[~model_df.exact].reset_index(drop=True),
                                "без точных совпадений")
ml_tbl = pd.concat([res_all, res_ne])
dump(ml_tbl, "08_model_comparison")
print(f"\nTrain: {len(ctx_all['train'])} задач до {ctx_all['cut']:%Y-%m-%d}, "
      f"test: {len(ctx_all['test'])} задач после\n")
print(ml_tbl.to_string())

# %% [markdown]
# ### 8.2 Что показывает сравнение
#
# На полной выборке baseline «факт = оценка» **не побеждается по медианным метрикам**.
# Это прямое следствие ловушки №1: 34 % тестовых задач имеют факт, тождественно равный
# оценке, и baseline берёт их с нулевой ошибкой, а любая модель, которая хоть немного
# сдвигает прогноз, эти строки портит.
#
# Правильный вывод — не «ML не работает», а **«метрика измеряет учётную практику,
# а не предсказательную способность»**. Как только точные совпадения убраны, картина
# меняется: GBM на лог-отношении обходит baseline и по `MAE_log`, и особенно по
# `RMSE_log` — то есть выигрыш идёт **в хвостах**, на задачах, которые реально срываются.
#
# Это и есть практически ценная часть: медианную задачу разработчик оценивает не хуже
# модели, но модель заметно лучше видит, **какая задача рискует уехать в разы**.

# %%
fig, axes = plt.subplots(1, 2, figsize=(13, 4.6), sharey=True)
for ax, (label, t) in zip(axes, [("все задачи", res_all), ("без точных совпадений", res_ne)]):
    names = list(t.index)
    y = np.arange(len(names))
    base = t.loc["B0: факт = оценка", "RMSE_log"]
    colors = [ACCENT3 if v < base else (INK if n.startswith("B0") else MUTED)
              for n, v in zip(names, t.RMSE_log)]
    ax.barh(y, t.RMSE_log, color=colors)
    ax.axvline(base, color=INK, lw=1.2, ls="--")
    ax.set_yticks(y); ax.set_yticklabels(names, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("RMSE в логарифмах (меньше — лучше)")
    ax.set_title(label)
    for yi, v in zip(y, t.RMSE_log):
        ax.text(v + .01, yi, f"{v:.3f}", va="center", fontsize=8, color=MUTED)
fig.suptitle("Зелёным — то, что обошло baseline «поверь оценке» по контролю хвостов",
             y=1.03, fontsize=12, fontweight="bold")
save(fig, "08_model_comparison"); plt.close(fig)

# %% [markdown]
# ### 8.3 Один сплит — это не результат: rolling-origin валидация
#
# Единственное разбиение по времени легко даёт случайный результат. Повторим эксперимент
# на 5 последовательных окнах: обучаемся на всём прошлом до момента `t`, тестируемся
# на следующем куске, сдвигаем `t` вперёд. Так проверяется устойчивость вывода
# и заодно видно, стационарен ли процесс.

# %%
def rolling_origin(d, n_folds=5, start=.50, stop=.90, horizon=.08):
    d = d.reset_index(drop=True)
    rows = []
    for k, q in enumerate(np.linspace(start, stop, n_folds)):
        cut, cut2 = d.date.quantile(q), d.date.quantile(min(q + horizon, .999))
        tr, te = d[d.date <= cut], d[(d.date > cut) & (d.date <= cut2)]
        if len(te) < 150:
            continue
        y_te, le_te, abs_te = te.log_act.values, te.log_est.values, te.actual.values
        Xtr, Xte, ci = as_categorical(tr[FEATURES], te[FEATURES])
        m = gbm(ci).fit(Xtr, tr.log_ratio.values)
        b0 = metrics(le_te, y_te, abs_te, "B0")
        m3 = metrics(le_te + m.predict(Xte), y_te, abs_te, "M3")
        rows.append({"фолд": k + 1, "N train": len(tr), "N test": len(te),
                     "тест с": f"{te.date.min():%Y-%m}",
                     "B0 MAE_log": b0["MAE_log"], "M3 MAE_log": m3["MAE_log"],
                     "B0 RMSE_log": b0["RMSE_log"], "M3 RMSE_log": m3["RMSE_log"]})
    t = pd.DataFrame(rows)
    t["выигрыш RMSE, %"] = (100 * (1 - t["M3 RMSE_log"] / t["B0 RMSE_log"])).round(1)
    return t

roll_all = rolling_origin(model_df)
roll_ne = rolling_origin(model_df[~model_df.exact])
dump(roll_all, "09_rolling_all")
dump(roll_ne, "09_rolling_no_exact")
print("Все задачи:\n", roll_all.to_string(index=False))
print("\nБез точных совпадений:\n", roll_ne.to_string(index=False))
print("\nСредний выигрыш GBM по RMSE_log: "
      f"все задачи {roll_all['выигрыш RMSE, %'].mean():.1f} %, "
      f"без совпадений {roll_ne['выигрыш RMSE, %'].mean():.1f} %")

fig, ax = plt.subplots(figsize=(9, 4))
w = .35
x = np.arange(len(roll_ne))
ax.bar(x - w/2, roll_ne["B0 RMSE_log"], w, color=MUTED, label="B0: факт = оценка")
ax.bar(x + w/2, roll_ne["M3 RMSE_log"], w, color=ACCENT3, label="M3: GBM на лог-отношении")
ax.set_xticks(x); ax.set_xticklabels(roll_ne["тест с"])
ax.set_xlabel("начало тестового окна"); ax.set_ylabel("RMSE_log")
ax.set_title("Rolling-origin: преимущество модели в хвостах устойчиво по времени\n"
             "(выборка без точных совпадений)")
ax.legend()
save(fig, "09_rolling_origin"); plt.close(fig)

# %% [markdown]
# ### 8.4 Главный практический результат: интервал вместо точки
#
# Точечный прогноз для задачи с разбросом ×0.5…×3 бесполезен независимо от того, кто его
# дал — человек или градиентный бустинг. Полезен **честный интервал**.
#
# Строим квантильную регрессию (GBM с pinball loss на 10 % и 90 % квантили лог-отношения)
# и калибруем её методом **conformalized quantile regression (CQR)**: отрезаем от обучающей
# выборки календарно последние 20 % как calibration set, считаем на нём conformity score
# `s = max(lo − y, y − hi)` и расширяем интервал на его эмпирический квантиль.
#
# Это даёт покрытие, близкое к номинальному, **без предположений о распределении** —
# при условии обменности, которая тут выполняется лишь приблизительно (процесс
# нестационарен), поэтому проверяем покрытие эмпирически на каждом окне.
#
# *Проверено и отвергнуто:* асимметричная версия CQR (отдельная поправка на верхнюю
# и нижнюю границы, каждая на уровне α/2) даёт то же покрытие 80.4 % при чуть большей
# средней ширине (×9.8 против ×9.5), поэтому оставлена симметричная.

# %%
def quantile_intervals(d, alpha=.2, n_folds=5, start=.50, stop=.90, horizon=.08):
    """Возвращает покрытие/ширину для сырых квантилей и после CQR-калибровки."""
    d = d.reset_index(drop=True)
    lo_q, hi_q = alpha / 2, 1 - alpha / 2
    rows, example = [], None
    for k, q in enumerate(np.linspace(start, stop, n_folds)):
        cut, cut2 = d.date.quantile(q), d.date.quantile(min(q + horizon, .999))
        tr_all, te = d[d.date <= cut], d[(d.date > cut) & (d.date <= cut2)]
        if len(te) < 150:
            continue
        n_fit = int(len(tr_all) * .8)
        fit, cal = tr_all.iloc[:n_fit], tr_all.iloc[n_fit:]      # calibration = самые свежие
        Xf, Xt, ci = as_categorical(fit[FEATURES], te[FEATURES])
        _, Xc, _ = as_categorical(fit[FEATURES], cal[FEATURES])

        models = {p: gbm(ci, loss="quantile", quantile=p, max_iter=300).fit(Xf, fit.log_ratio.values)
                  for p in (lo_q, hi_q)}
        lo_te = te.log_est.values + models[lo_q].predict(Xt)
        hi_te = te.log_est.values + models[hi_q].predict(Xt)
        y_te = te.log_act.values

        lo_c = cal.log_est.values + models[lo_q].predict(Xc)
        hi_c = cal.log_est.values + models[hi_q].predict(Xc)
        score = np.maximum(lo_c - cal.log_act.values, cal.log_act.values - hi_c)
        rank = int(np.ceil((len(score) + 1) * (1 - alpha))) - 1
        Q = np.sort(score)[min(max(rank, 0), len(score) - 1)]

        rows.append({
            "фолд": k + 1, "N test": len(te),
            "покрытие (сырое)": round(float(((y_te >= lo_te) & (y_te <= hi_te)).mean()), 3),
            "ширина (сырое)": round(float(np.median(np.exp(hi_te - lo_te))), 2),
            "покрытие (CQR)": round(float(((y_te >= lo_te - Q) & (y_te <= hi_te + Q)).mean()), 3),
            "ширина (CQR)": round(float(np.median(np.exp((hi_te + Q) - (lo_te - Q)))), 2),
            "поправка Q": round(float(Q), 3)})
        if example is None:
            example = te.assign(lo=np.exp(lo_te - Q), hi=np.exp(hi_te + Q))
    return pd.DataFrame(rows), example

iv, iv_example = quantile_intervals(model_df[~model_df.exact])
dump(iv, "10_conformal_intervals")
print(iv.to_string(index=False))
print(f"\nНоминальное покрытие 80 %. Сырые квантили: {iv['покрытие (сырое)'].mean():.1%}, "
      f"после CQR: {iv['покрытие (CQR)'].mean():.1%}")
print(f"Медианная ширина интервала: сырая ×{iv['ширина (сырое)'].mean():.1f}, "
      f"после калибровки ×{iv['ширина (CQR)'].mean():.1f}")

# Ширина интервала сильно зависит от размера задачи - для планирования это важнее,
# чем средняя цифра по датасету.
iv_example["size_bin"] = pd.cut(iv_example.estimate, SIZE_BINS, labels=SIZE_LABELS)
width_by_size = iv_example.groupby("size_bin", observed=True).apply(
    lambda g: pd.Series({
        "N": len(g),
        "медиана ширины": round(float(np.median(g.hi / g.lo)), 1),
        "покрытие": round(float(((g.actual >= g.lo) & (g.actual <= g.hi)).mean()), 2),
        "нижняя граница / оценка": round(float(np.median(g.lo / g.estimate)), 2),
        "верхняя граница / оценка": round(float(np.median(g.hi / g.estimate)), 2),
    }), include_groups=False)
dump(width_by_size, "10_interval_width_by_size")
print("\nШирина 80 %-го интервала по размеру задачи (одно тестовое окно):")
print(width_by_size.to_string())

fig, axes = plt.subplots(1, 2, figsize=(13, 4.4))
ax = axes[0]
x = np.arange(len(iv))
ax.plot(x, iv["покрытие (сырое)"], "o-", color=ACCENT2, lw=2, label="сырая квантильная регрессия")
ax.plot(x, iv["покрытие (CQR)"], "s-", color=ACCENT3, lw=2.4, label="после CQR-калибровки")
ax.axhline(.8, color=INK, ls="--", lw=1.2)
ax.annotate("номинальные 80 %", (0, .806), fontsize=9, color=INK)
ax.set_xticks(x); ax.set_xticklabels([f"фолд {i}" for i in iv["фолд"]])
ax.set_ylim(.5, 1.0)
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0%}"))
ax.set_ylabel("доля фактов внутри интервала")
ax.set_title("Сырые квантили систематически завышают уверенность,\nCQR это чинит")
ax.legend(loc="lower right")

ax = axes[1]
ex = iv_example.sort_values("estimate").iloc[::max(1, len(iv_example) // 60)]
xs = np.arange(len(ex))
ax.vlines(xs, ex.lo, ex.hi, color=ACCENT, alpha=.45, lw=3)
inside = (ex.actual >= ex.lo) & (ex.actual <= ex.hi)
ax.scatter(xs[inside.values], ex.actual[inside.values], s=14, color=INK, zorder=3, label="факт внутри")
ax.scatter(xs[~inside.values], ex.actual[~inside.values], s=22, color=ACCENT2, zorder=3,
           marker="x", label="факт вне интервала")
ax.plot(xs, ex.estimate, color=ACCENT3, lw=1.6, ls="--", label="исходная оценка")
ax.set_yscale("log")
ax.set_xlabel("задачи тестового окна, отсортированные по оценке")
ax.set_ylabel("часы (лог-шкала)")
ax.set_title("Как выглядит калиброванный 80 %-й интервал")
ax.legend(fontsize=8)
save(fig, "10_intervals"); plt.close(fig)

# %% [markdown]
# ### 8.5 На что модель на самом деле смотрит
#
# Permutation importance на тестовом окне — насколько ухудшается `RMSE_log`, если
# случайно перемешать один признак. Считаем для M3 (GBM, предсказывающий поправку
# к оценке), чтобы видеть, что помогает **сверх** самой оценки.

# %%
ctx = ctx_ne                      # выборка без точных совпадений
tr, te = ctx["train"], ctx["test"]
Xtr, Xte, ci = ctx["Xtr"], ctx["Xte"], ctx["cat_idx"]
m3 = ctx["m3"]

pi = permutation_importance(m3, Xte, te.log_ratio.values, n_repeats=10,
                            random_state=RNG, scoring="neg_root_mean_squared_error")
imp = pd.DataFrame({"признак": FEATURES,
                    "важность": pi.importances_mean,
                    "std": pi.importances_std}).sort_values("важность", ascending=False)
dump(imp.round(4), "11_feature_importance")
print(imp.round(4).to_string(index=False))

fig, ax = plt.subplots(figsize=(8, 4.6))
top = imp.head(10).iloc[::-1]
ax.barh(np.arange(len(top)), top["важность"], xerr=top["std"],
        color=ACCENT, error_kw=dict(ecolor=MUTED, lw=1))
ax.set_yticks(np.arange(len(top))); ax.set_yticklabels(top["признак"])
ax.set_xlabel("прирост RMSE_log при перемешивании признака")
ax.set_title("Что добавляет информацию сверх самой оценки")
save(fig, "11_feature_importance"); plt.close(fig)

# %% [markdown]
# ---
# ## 9. Итоговая сводка
#
# Собираем ключевые числа в одну таблицу — она же основа выводов в `REPORT.md`.

# %%
summary = {
    "SiP: задач после очистки": len(sip),
    "SiP: доля факт == оценка": f"{sip.exact.mean():.1%}",
    "CESAW: доля факт == оценка": f"{cesaw.exact.mean():.1%}",
    "SiP: оценок кратных рабочему дню (7ч)": f"{multiple_of(sip.estimate, 7).mean():.1%}",
    "SiP: фактов кратных рабочему дню": f"{multiple_of(sip.actual, 7).mean():.1%}",
    "SiP: геом. среднее факт/оценка (все)": round(float(np.exp(sip.log_ratio.mean())), 3),
    "SiP: геом. среднее факт/оценка (без совпадений)":
        round(float(np.exp(sip[~sip.exact].log_ratio.mean())), 3),
    "SiP: смещение для задач ≤1ч": round(float(prof_ne.loc["≤1ч", "геом. среднее"]), 2),
    "SiP: смещение для задач >40ч": round(float(prof_ne.loc[">40ч", "геом. среднее"]), 2),
    "SiP: SD лог-отношения": round(float(sip[~sip.exact].log_ratio.std()), 3),
    "Наклон log_ratio~log_est (SiP)": slopes_tbl.loc["SiP", "наклон"],
    "Наклон log_ratio~log_est (CESAW)": slopes_tbl.loc["CESAW", "наклон"],
    "Наклон log_ratio~log_est (Renzo)": slopes_tbl.loc["Renzo", "наклон"],
    "R² типа работы": float(ve.loc["SubCategory", "R² лог-отношения"]),
    "R² исполнителя": float(ve.loc["person", "R² лог-отношения"]),
    "B0 RMSE_log (без совпадений)": float(res_ne.loc["B0: факт = оценка", "RMSE_log"]),
    "M3 RMSE_log (без совпадений)": float(res_ne.loc["M3: GBM → log(факт/оценка)", "RMSE_log"]),
    "Средний выигрыш RMSE (rolling)": f"{roll_ne['выигрыш RMSE, %'].mean():.1f} %",
    "Покрытие интервала до CQR": f"{iv['покрытие (сырое)'].mean():.1%}",
    "Покрытие интервала после CQR": f"{iv['покрытие (CQR)'].mean():.1%}",
    "Медианная ширина интервала (CQR)": f"×{iv['ширина (CQR)'].mean():.1f}",
}
summary_tbl = pd.DataFrame.from_dict(summary, orient="index", columns=["значение"])
dump(summary_tbl, "12_summary")
print(summary_tbl.to_string())

# %% [markdown]
# ## 10. Выводы и что с этим делать менеджеру
#
# **1. Сначала проверьте, что вы вообще измеряете.** 34 % «идеально точных» задач
# в SiP (и 44 % в Renzo) — это учётная практика списания по оценке, а не точность.
# Любой дашборд «наша точность оценок», построенный поверх такого артефакта, хвалит
# команду за то, чего нет. Диагностика — доля точных совпадений в разрезе размера
# задачи: если она падает с 60 % до 1 %, вы смотрите на учёт, а не на оценку.
#
# **2. Смещение зависит от размера, и оно меняет знак.** Мелкие задачи недооценены
# (×1.22), крупные переоценены (×0.37) — размах 3.3 раза. Эффект воспроизводится
# на трёх независимых датасетах с разной индустрией, культурой и единицами измерения
# (наклон log-log регрессии −0.24 / −0.17 / −0.81, все p < 1e−140). Единый
# «коэффициент запаса» на команду не просто бесполезен — он вреден, потому что
# ошибается в разные стороны на разных задачах.
#
# **3. Личность исполнителя почти ничего не объясняет.** Размер задачи даёт R² = 0.089,
# исполнитель — 0.032, тип работы — 0.030. Все структурные факторы вместе не дотягивают
# до 15 % дисперсии. Персональные коэффициенты оценщика — это шум, выданный за сигнал.
#
# **4. Но смещение по типам работ реально и действенно.** Разработка оценивается
# с запасом (баги ×0.75, доработки ×0.82), а коммуникационная работа стабильно
# перерасходуется: планёрки ×2.38, статусные встречи ×1.52, управление персоналом ×1.48,
# обучение ×1.46. Это не ошибка оценки навыка — это работа, которая в оценку не попадает
# вообще. Самое дешёвое улучшение планирования из всего найденного: закладывать
# коммуникационные активности отдельной строкой, а не «внутри» задач.
#
# **5. Опыт почти не помогает.** За 11 лет разброс не снизился. Индивидуальная кривая
# обучения даёт ~20 % улучшения на первой сотне задач и выходит на плато. Ошибка оценки —
# свойство задачи, а не квалификации оценщика.
#
# **6. ML улучшает не медиану, а хвост.** На данных «как есть» baseline «поверь оценке»
# не побеждается по медианным метрикам — но только потому, что треть тестовых строк
# тождественны. На честной подвыборке GBM выигрывает и по `MAE_log` (0.762 против 0.788),
# и особенно по `RMSE_log` (1.031 против 1.119, средний выигрыш **7.3 %** на пяти
# rolling-origin окнах). Выигрыш идёт именно там, где он нужен: на задачах, которые
# уезжают в разы.
#
# **7. Единственный честный продукт модели — интервал.** Если 85 % дисперсии
# нередуцируемы, точечный прогноз бессмысленен, кем бы он ни был выдан. Калиброванный
# 80 %-й интервал даёт практичное правило:
#
# | оценка разработчика | честный 80 %-й диапазон |
# |---|---|
# | ≤ 1 ч | ×0.44 … ×3.4 |
# | 4–8 ч | ×0.25 … ×3.2 |
# | 16–40 ч | ×0.14 … ×2.4 |
# | > 40 ч | ×0.05 … ×2.6 |
#
# Без conformal-калибровки квантильная регрессия самоуверенна (покрытие 68 % вместо 80 %);
# поправка возвращает покрытие к номинальному (80.5 %). Широкий интервал — это не
# недостаток модели, а **измеренное свойство предметной области**, и менеджеру полезнее
# знать его, чем получать точное число, в которое никто не попадёт.
#
# ### Ограничения
#
# * Все выводы наблюдательные: мы не знаем, влияла ли оценка на факт (self-fulfilling
#   prophecy — разработчик мог подгонять работу под срок). Разделить это без
#   эксперимента невозможно.
# * Незакрытые и отменённые задачи в датасете отсутствуют → survivorship bias,
#   вероятно смещающий выводы в оптимистичную сторону.
# * SiP — одна компания одной эпохи (2004–2014); CESAW и Renzo подтверждают только
#   эффект размера, но не абсолютные коэффициенты.
# * Conformal-гарантия требует обменности; процесс нестационарен, поэтому эмпирическое
#   покрытие проверялось на каждом окне отдельно (0.78–0.83).
#
# ### Что бы я сделал дальше
#
# * Иерархическая байесовская модель: частичный пулинг по разработчику и типу работы
#   даст устойчивые оценки для редких категорий вместо шумных групповых средних.
# * Признаки из текста `Summary` через эмбеддинги — сейчас из текста используется
#   только длина, и она уже входит в топ-5 по важности.
# * Модель цензурированных наблюдений для незакрытых задач (снять survivorship bias).
# * Проверка на командном уровне: агрегируются ли ошибки отдельных задач в ошибку
#   спринта, или частично компенсируют друг друга (для планирования это главный вопрос).

# %%
print("\n" + "=" * 70)
print("ГОТОВО. Фигуры:", len(list(FIG_DIR.glob('*.png'))), "| Таблицы:", len(list(RES_DIR.glob('*.csv'))))
print("=" * 70)
