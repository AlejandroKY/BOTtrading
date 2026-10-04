import pandas as pd

from futbot.data import load_csv


def test_mt5_server_time_is_new_york_plus_7(tmp_path):
    # 16:30 del servidor = 9:30 de Nueva York, en verano (UTC+3) y en invierno (UTC+2)
    raw = pd.DataFrame({"time": ["2026-07-01 16:30:00+00:00", "2026-01-15 16:30:00+00:00"],
                        "open": [1.0, 1.0], "high": [1.0, 1.0], "low": [1.0, 1.0], "close": [1.0, 1.0],
                        "volume": [1, 1], "spread": [5, 5]})
    path = tmp_path / "US100_M1.csv.gz"
    raw.to_csv(path, index=False)
    df = load_csv(str(path), tz="mt5")
    assert [t.strftime("%Y-%m-%d %H:%M") for t in df.index] == ["2026-01-15 09:30", "2026-07-01 09:30"]
    assert str(df.index.tz) == "America/New_York"
