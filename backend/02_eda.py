"""
02_eda.py
전처리된 CSV를 읽어 EDA 시각화 수행
→ eda_output/ 폴더에 PNG 파일로 저장

변경사항:
  - 미세먼지(pm1, pm25, pm10) 시각화 추가
  - 이벤트 발생 시점 시계열에 표시
  - 환기 이벤트 전후 비교 차트 추가

실행:
    pip install pandas matplotlib seaborn
    python 02_eda.py
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns
import warnings

warnings.filterwarnings("ignore")


# ── 한글 폰트 설정 ────────────────────────────────────────────────────────────
def set_korean_font():
    candidates = ["AppleGothic", "NanumGothic", "Malgun Gothic", "DejaVu Sans"]
    available  = {f.name for f in fm.fontManager.ttflist}
    for c in candidates:
        if c in available:
            plt.rcParams["font.family"]       = c
            plt.rcParams["axes.unicode_minus"] = False
            print(f"한글 폰트 설정: {c}")
            return
    print("[경고] 한글 폰트 없음")

set_korean_font()

OUTPUT_DIR = "eda_output"
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ── 데이터 로드 ───────────────────────────────────────────────────────────────
def load(path: str = "sensor_cleaned.csv") -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["recorded_at"])
    print(f"[로드] {len(df):,} 행")
    return df


# ── EDA 1. 기술 통계 ──────────────────────────────────────────────────────────
def eda_stats(df: pd.DataFrame) -> None:
    print("\n" + "="*50)
    print("EDA 1: 기술 통계")
    print("="*50)
    cols = ["temperature", "humidity", "pm1", "pm25", "pm10"]
    cols = [c for c in cols if c in df.columns]
    print(df[cols].describe().round(2).to_string())


# ── EDA 2. 시계열 시각화 (이벤트 포함) ───────────────────────────────────────
def eda_timeseries(df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)
    fig.suptitle("온도·습도·미세먼지 시계열", fontsize=14)

    # 이벤트 발생 시점
    event_rows = df[df["event"].notna()] if "event" in df.columns else pd.DataFrame()

    # 온도
    axes[0].plot(df["recorded_at"], df["temperature"],
                 color="#E8593C", lw=0.5, alpha=0.5, label="원본")
    if "temp_ma60" in df.columns:
        axes[0].plot(df["recorded_at"], df["temp_ma60"],
                     color="#A32D2D", lw=1.5, label="이동평균(1h)")
    for _, row in event_rows.iterrows():
        axes[0].axvline(row["recorded_at"], color="green", lw=1.5, ls="--", alpha=0.7)
        axes[0].text(row["recorded_at"], axes[0].get_ylim()[1] if axes[0].get_ylim()[1] != 0 else 30,
                     str(row["event"]), fontsize=7, color="green", rotation=45)
    axes[0].set_ylabel("온도 (°C)")
    axes[0].legend(fontsize=9)
    axes[0].grid(alpha=0.3)

    # 습도
    axes[1].plot(df["recorded_at"], df["humidity"],
                 color="#3B8BD4", lw=0.5, alpha=0.5, label="원본")
    if "humi_ma60" in df.columns:
        axes[1].plot(df["recorded_at"], df["humi_ma60"],
                     color="#0C447C", lw=1.5, label="이동평균(1h)")
    for _, row in event_rows.iterrows():
        axes[1].axvline(row["recorded_at"], color="green", lw=1.5, ls="--", alpha=0.7)
    axes[1].set_ylabel("습도 (%)")
    axes[1].legend(fontsize=9)
    axes[1].grid(alpha=0.3)

    # 미세먼지
    if "pm25" in df.columns:
        axes[2].plot(df["recorded_at"], df["pm25"],
                     color="#854F0B", lw=0.5, alpha=0.5, label="PM2.5 원본")
        if "pm25_ma60" in df.columns:
            axes[2].plot(df["recorded_at"], df["pm25_ma60"],
                         color="#412402", lw=1.5, label="PM2.5 이동평균(1h)")
        if "pm10" in df.columns:
            axes[2].plot(df["recorded_at"], df["pm10"],
                         color="#EF9F27", lw=0.5, alpha=0.4, label="PM10")
        for _, row in event_rows.iterrows():
            axes[2].axvline(row["recorded_at"], color="green", lw=1.5, ls="--", alpha=0.7)
        axes[2].set_ylabel("미세먼지 (μg/m³)")
        axes[2].legend(fontsize=9)
        axes[2].grid(alpha=0.3)

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "01_timeseries.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  저장: {path}")


# ── EDA 3. 분포 시각화 ────────────────────────────────────────────────────────
def eda_distribution(df: pd.DataFrame) -> None:
    cols = [
        ("temperature", "#E8593C", "온도 (°C)"),
        ("humidity",    "#3B8BD4", "습도 (%)"),
        ("pm25",        "#854F0B", "PM2.5 (μg/m³)"),
        ("pm10",        "#EF9F27", "PM10 (μg/m³)"),
    ]
    cols = [(c, color, label) for c, color, label in cols if c in df.columns]

    fig, axes = plt.subplots(len(cols), 2, figsize=(12, 4 * len(cols)))
    fig.suptitle("센서 데이터 분포", fontsize=14)

    for i, (col, color, label) in enumerate(cols):
        axes[i][0].hist(df[col], bins=50, color=color, alpha=0.7, edgecolor="white")
        axes[i][0].axvline(df[col].mean(), color="black", lw=1.5, ls="--",
                           label=f"평균: {df[col].mean():.1f}")
        axes[i][0].axvline(df[col].median(), color="gray", lw=1.5, ls=":",
                           label=f"중앙값: {df[col].median():.1f}")
        axes[i][0].set_title(f"{label} 히스토그램")
        axes[i][0].set_xlabel(label)
        axes[i][0].legend(fontsize=9)

        axes[i][1].boxplot(df[col], vert=True, patch_artist=True,
                           boxprops=dict(facecolor=color, alpha=0.5),
                           medianprops=dict(color="black", lw=2))
        axes[i][1].set_title(f"{label} 박스플롯")
        axes[i][1].set_ylabel(label)

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "02_distribution.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  저장: {path}")


# ── EDA 4. 시간대별 평균 ──────────────────────────────────────────────────────
def eda_hourly_pattern(df: pd.DataFrame) -> None:
    cols = ["temperature", "humidity", "pm25", "pm10"]
    cols = [c for c in cols if c in df.columns]
    hourly = df.groupby("hour")[cols].agg(["mean", "std"])

    fig, axes = plt.subplots(2, 1, figsize=(12, 8))
    fig.suptitle("시간대별 평균 (±1σ)", fontsize=14)

    # 온도/습도
    ax1 = axes[0]
    ax2 = ax1.twinx()
    temp_mean = hourly["temperature"]["mean"]
    temp_std  = hourly["temperature"]["std"]
    humi_mean = hourly["humidity"]["mean"]
    humi_std  = hourly["humidity"]["std"]

    ax1.plot(temp_mean.index, temp_mean.values, "o-", color="#E8593C", lw=2, label="온도 평균")
    ax1.fill_between(temp_mean.index, temp_mean - temp_std, temp_mean + temp_std,
                     color="#E8593C", alpha=0.15)
    ax2.plot(humi_mean.index, humi_mean.values, "s--", color="#3B8BD4", lw=2, label="습도 평균")
    ax2.fill_between(humi_mean.index, humi_mean - humi_std, humi_mean + humi_std,
                     color="#3B8BD4", alpha=0.12)
    ax1.set_ylabel("온도 (°C)", color="#E8593C")
    ax2.set_ylabel("습도 (%)", color="#3B8BD4")
    ax1.set_xticks(range(0, 24))
    ax1.set_title("온도·습도")
    ax1.grid(alpha=0.3)

    # 미세먼지
    ax3 = axes[1]
    if "pm25" in hourly.columns:
        pm25_mean = hourly["pm25"]["mean"]
        pm10_mean = hourly["pm10"]["mean"] if "pm10" in hourly.columns else None
        ax3.plot(pm25_mean.index, pm25_mean.values, "o-", color="#854F0B", lw=2, label="PM2.5 평균")
        if pm10_mean is not None:
            ax3.plot(pm10_mean.index, pm10_mean.values, "s--", color="#EF9F27", lw=2, label="PM10 평균")
    ax3.set_ylabel("미세먼지 (μg/m³)")
    ax3.set_xticks(range(0, 24))
    ax3.set_title("미세먼지")
    ax3.legend(fontsize=9)
    ax3.grid(alpha=0.3)

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "03_hourly_pattern.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  저장: {path}")


# ── EDA 5. 요일×시간대 히트맵 ────────────────────────────────────────────────
def eda_heatmap(df: pd.DataFrame) -> None:
    if "day_of_week" not in df.columns:
        df["day_of_week"] = pd.to_datetime(df["recorded_at"]).dt.dayofweek

    dow_labels = ["월", "화", "수", "목", "금", "토", "일"]
    plot_cols = [
        ("temperature", "YlOrRd", "온도 (°C)"),
        ("humidity",    "YlGnBu", "습도 (%)"),
        ("pm25",        "YlOrBr", "PM2.5 (μg/m³)"),
    ]
    plot_cols = [(c, cmap, title) for c, cmap, title in plot_cols if c in df.columns]

    fig, axes = plt.subplots(1, len(plot_cols), figsize=(8 * len(plot_cols), 5))
    if len(plot_cols) == 1:
        axes = [axes]
    fig.suptitle("요일 × 시간대 평균 히트맵", fontsize=14)

    for ax, (col, cmap, title) in zip(axes, plot_cols):
        pivot = df.pivot_table(values=col, index="day_of_week",
                               columns="hour", aggfunc="mean")
        pivot.index = [dow_labels[i] for i in pivot.index if i < 7]
        sns.heatmap(pivot, ax=ax, cmap=cmap, annot=True, fmt=".1f",
                    linewidths=0.3, annot_kws={"size": 7},
                    cbar_kws={"label": title})
        ax.set_title(title)
        ax.set_xlabel("시간 (h)")
        ax.set_ylabel("요일")

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "04_heatmap.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  저장: {path}")


# ── EDA 6. 상관관계 ───────────────────────────────────────────────────────────
def eda_correlation(df: pd.DataFrame) -> None:
    cols = ["temperature", "humidity", "pm1", "pm25", "pm10",
            "hour", "day_of_week", "is_weekend", "temp_diff", "humi_diff", "pm25_diff"]
    cols = [c for c in cols if c in df.columns]
    corr = df[cols].corr()

    fig, ax = plt.subplots(figsize=(12, 10))
    import numpy as np
    mask = np.triu(np.ones_like(corr, dtype=bool))
    sns.heatmap(corr, ax=ax, mask=mask, annot=True, fmt=".2f",
                cmap="coolwarm", center=0, linewidths=0.5,
                annot_kws={"size": 8})
    ax.set_title("피처 간 상관관계 (하삼각)")
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "05_correlation.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  저장: {path}")


# ── EDA 7. 이벤트 전후 비교 ──────────────────────────────────────────────────
def eda_event_impact(df: pd.DataFrame) -> None:
    """환기 이벤트 전후 온습도·미세먼지 변화 분석"""
    if "event" not in df.columns:
        print("  이벤트 데이터 없음 - 건너뜀")
        return

    event_rows = df[df["event"].notna()]
    if event_rows.empty:
        print("  이벤트 없음 - 건너뜀")
        return

    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)
    fig.suptitle("이벤트 전후 변화", fontsize=14)

    cols_info = [
        ("temperature", "#E8593C", "온도 (°C)"),
        ("humidity",    "#3B8BD4", "습도 (%)"),
        ("pm25",        "#854F0B", "PM2.5 (μg/m³)"),
    ]

    for ax, (col, color, label) in zip(axes, cols_info):
        if col not in df.columns:
            continue
        ax.plot(df["recorded_at"], df[col], color=color, lw=0.8, alpha=0.7, label=label)
        for _, row in event_rows.iterrows():
            ax.axvline(row["recorded_at"], color="green", lw=2, ls="--", alpha=0.8)
            ax.text(row["recorded_at"], df[col].max() * 0.95,
                    str(row["event"]), fontsize=8, color="green", rotation=45)
        ax.set_ylabel(label)
        ax.legend(fontsize=9)
        ax.grid(alpha=0.3)

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "06_event_impact.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  저장: {path}")


# ── EDA 8. 일별 추이 ─────────────────────────────────────────────────────────
def eda_daily_trend(df: pd.DataFrame) -> None:
    if "date" not in df.columns:
        df["date"] = pd.to_datetime(df["recorded_at"]).dt.date

    cols = ["temperature", "humidity", "pm25", "pm10"]
    cols = [c for c in cols if c in df.columns]
    daily = df.groupby("date")[cols].mean()

    fig, (ax1, ax3) = plt.subplots(2, 1, figsize=(14, 8))

    # 온습도
    ax2 = ax1.twinx()
    ax1.bar(range(len(daily)), daily["temperature"], color="#E8593C", alpha=0.6, label="온도 평균")
    ax2.plot(range(len(daily)), daily["humidity"], "o-", color="#3B8BD4", lw=1.5, ms=4, label="습도 평균")
    ax1.set_ylabel("온도 (°C)", color="#E8593C")
    ax2.set_ylabel("습도 (%)", color="#3B8BD4")
    ax1.set_title("일별 평균 온도·습도")
    ax1.grid(alpha=0.3)
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=9)

    # 미세먼지
    if "pm25" in daily.columns:
        ax3.plot(range(len(daily)), daily["pm25"], "o-", color="#854F0B", lw=1.5, ms=4, label="PM2.5 평균")
        if "pm10" in daily.columns:
            ax3.plot(range(len(daily)), daily["pm10"], "s--", color="#EF9F27", lw=1.5, ms=4, label="PM10 평균")
        ax3.set_xticks(range(0, len(daily), max(1, len(daily)//10)))
        ax3.set_xticklabels(
            [str(d) for d in daily.index[::max(1, len(daily)//10)]],
            rotation=30, ha="right", fontsize=8
        )
        ax3.set_ylabel("미세먼지 (μg/m³)")
        ax3.set_title("일별 평균 미세먼지")
        ax3.legend(fontsize=9)
        ax3.grid(alpha=0.3)

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "07_daily_trend.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  저장: {path}")


# ── 메인 ─────────────────────────────────────────────────────────────────────
def main():
    print("===== EDA 시작 =====\n")
    df = load("sensor_cleaned.csv")

    print("\n[EDA 1] 기술 통계")
    eda_stats(df)
    print("\n[EDA 2] 시계열 시각화")
    eda_timeseries(df)
    print("\n[EDA 3] 분포 시각화")
    eda_distribution(df)
    print("\n[EDA 4] 시간대별 패턴")
    eda_hourly_pattern(df)
    print("\n[EDA 5] 요일×시간대 히트맵")
    eda_heatmap(df)
    print("\n[EDA 6] 상관관계")
    eda_correlation(df)
    print("\n[EDA 7] 이벤트 전후 비교")
    eda_event_impact(df)
    print("\n[EDA 8] 일별 추이")
    eda_daily_trend(df)

    print(f"\n===== EDA 완료 =====")
    print(f"결과 파일: {OUTPUT_DIR}/ 폴더 확인")


if __name__ == "__main__":
    main()
