"""
03_train_model.py
sensor_cleaned.csv를 읽어 ML 모델 학습 후 저장

변경사항:
  - 미세먼지(pm25, pm10) 피처 추가
  - pm25 예측 모델 추가
  - 이벤트(has_event) 피처 추가

실행:
    pip install scikit-learn joblib pandas
    python 03_train_model.py
"""

import os
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import cross_val_score
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.preprocessing import StandardScaler

CSV_PATH  = "sensor_cleaned.csv"
MODEL_DIR = "models"
os.makedirs(MODEL_DIR, exist_ok=True)

# 모델 입력 피처
FEATURES = [
    "hour_sin", "hour_cos",
    "dow_sin",  "dow_cos",
    "is_weekend",
    "temp_ma60",
    "humi_ma60",
    "pm25_ma60",
    "temp_diff",
    "humi_diff",
    "pm25_diff",
    "has_event",
]


# ── 1. 데이터 로드 ────────────────────────────────────────────────────────────
def load_data() -> pd.DataFrame:
    df = pd.read_csv(CSV_PATH, parse_dates=["recorded_at"])
    print(f"[로드] {len(df):,} 행  /  기간: {df['recorded_at'].min()} ~ {df['recorded_at'].max()}")
    return df


# ── 2. 시간대별 평균 패턴 ─────────────────────────────────────────────────────
def make_hourly_pattern(df: pd.DataFrame) -> pd.DataFrame:
    cols = {"temperature": "target_temp", "humidity": "target_humi"}
    if "pm25" in df.columns:
        cols["pm25"] = "target_pm25"

    agg_dict = {new: (old, "mean") for old, new in cols.items()}
    agg_dict["count"] = ("temperature", "count")

    pattern = df.groupby(["hour", "is_weekend"]).agg(**agg_dict).reset_index().round(2)
    path = os.path.join(MODEL_DIR, "hourly_pattern.json")
    pattern.to_json(path, orient="records", force_ascii=False, indent=2)
    print(f"[패턴] 시간대별 패턴 저장: {path}  ({len(pattern)} 그룹)")
    return pattern


# ── 3. 학습 데이터 준비 ───────────────────────────────────────────────────────
def prepare_xy(df: pd.DataFrame):
    available = [f for f in FEATURES if f in df.columns]
    missing   = [f for f in FEATURES if f not in df.columns]
    if missing:
        print(f"[경고] 없는 피처 (건너뜀): {missing}")

    X  = df[available].copy()
    yt = df["temperature"].copy()
    yh = df["humidity"].copy()
    yp = df["pm25"].copy() if "pm25" in df.columns else None

    valid = X.notna().all(axis=1) & yt.notna() & yh.notna()
    X, yt, yh = X[valid], yt[valid], yh[valid]
    if yp is not None:
        yp = yp[valid]

    print(f"[준비] 학습 샘플: {len(X):,}  /  피처: {available}")
    return X, yt, yh, yp, available


# ── 4. 모델 학습 ──────────────────────────────────────────────────────────────
def train_model(X, y, target_name: str):
    print(f"\n  [{target_name}] 모델 학습 중...")

    rf = RandomForestRegressor(
        n_estimators=200, max_depth=8,
        min_samples_leaf=3, random_state=42, n_jobs=-1,
    )
    gb = GradientBoostingRegressor(
        n_estimators=200, max_depth=4,
        learning_rate=0.05, subsample=0.8, random_state=42,
    )

    cv_rf = -cross_val_score(rf, X, y, cv=5, scoring="neg_mean_absolute_error")
    cv_gb = -cross_val_score(gb, X, y, cv=5, scoring="neg_mean_absolute_error")

    print(f"    RandomForest   CV MAE: {cv_rf.mean():.4f} ± {cv_rf.std():.4f}")
    print(f"    GradientBoost  CV MAE: {cv_gb.mean():.4f} ± {cv_gb.std():.4f}")

    if cv_rf.mean() <= cv_gb.mean():
        best_model, chosen = rf, "RandomForest"
    else:
        best_model, chosen = gb, "GradientBoosting"

    print(f"    선택된 모델: {chosen}")
    best_model.fit(X, y)

    pred = best_model.predict(X)
    mae  = mean_absolute_error(y, pred)
    r2   = r2_score(y, pred)
    print(f"    최종 MAE: {mae:.4f}  /  R²: {r2:.4f}")

    return best_model, {"model": chosen, "cv_mae": round(float(cv_rf.mean()), 4),
                        "mae": round(mae, 4), "r2": round(r2, 4)}


# ── 5. 피처 중요도 출력 ───────────────────────────────────────────────────────
def print_feature_importance(model, feature_names: list, target: str):
    if not hasattr(model, "feature_importances_"):
        return
    imp = pd.Series(model.feature_importances_, index=feature_names).sort_values(ascending=False)
    print(f"\n  [{target}] 피처 중요도:")
    for feat, val in imp.items():
        bar = "█" * int(val * 40)
        print(f"    {feat:<15} {val:.4f}  {bar}")


# ── 메인 ─────────────────────────────────────────────────────────────────────
def main():
    print("===== 모델 학습 시작 =====\n")

    df = load_data()
    make_hourly_pattern(df)

    X, yt, yh, yp, feature_names = prepare_xy(df)

    scaler   = StandardScaler()
    X_scaled = pd.DataFrame(scaler.fit_transform(X), columns=feature_names)

    # 온도 모델
    print("\n[온도 모델]")
    model_temp, metrics_temp = train_model(X_scaled, yt, "온도")
    print_feature_importance(model_temp, feature_names, "온도")

    # 습도 모델
    print("\n[습도 모델]")
    model_humi, metrics_humi = train_model(X_scaled, yh, "습도")
    print_feature_importance(model_humi, feature_names, "습도")

    # 미세먼지 모델
    metrics_pm25 = {}
    if yp is not None:
        print("\n[PM2.5 모델]")
        model_pm25, metrics_pm25 = train_model(X_scaled, yp, "PM2.5")
        print_feature_importance(model_pm25, feature_names, "PM2.5")
        joblib.dump(model_pm25, os.path.join(MODEL_DIR, "model_pm25.pkl"))

    # 저장
    joblib.dump(model_temp,    os.path.join(MODEL_DIR, "model_temp.pkl"))
    joblib.dump(model_humi,    os.path.join(MODEL_DIR, "model_humi.pkl"))
    joblib.dump(scaler,        os.path.join(MODEL_DIR, "scaler.pkl"))
    joblib.dump(feature_names, os.path.join(MODEL_DIR, "feature_names.pkl"))

    import datetime
    meta = {
        "trained_at":   datetime.datetime.now().isoformat(),
        "n_samples":    int(len(X)),
        "features":     feature_names,
        "metrics_temp": metrics_temp,
        "metrics_humi": metrics_humi,
        "metrics_pm25": metrics_pm25,
    }
    with open(os.path.join(MODEL_DIR, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"\n===== 학습 완료 =====")
    print(f"저장 위치: {MODEL_DIR}/")


if __name__ == "__main__":
    main()
