# ============================================================
# 月相羅針 計算PoC v0.6｜入力UI・現在値改善
# 標準月相8分類（技術検証用）
#
# 注意：
# この分類名称・説明文章、および出生時間不明時の候補判定方式は、
# 春華独自の正式な「月相羅針」仕様ではありません。
#
# 春華独自仕様が確定するまでの間、計算・分類・画面表示を
# 検証するための仮データ／暫定技術仕様です。
# ============================================================

from __future__ import annotations


PHASES = [
    {
        "id": "P01",
        "name": "新月",
        "englishName": "New Moon",
        "start": 0.0,
        "end": 45.0,
        "description": (
            "新しいサイクルが始まる時期を象徴する月相です。"
            "一般的には、新しい目標を定めたり、これから始めたいことに"
            "意識を向ける段階として捉えられます。"
        ),
    },
    {
        "id": "P02",
        "name": "満ちていく三日月",
        "englishName": "Waxing Crescent",
        "start": 45.0,
        "end": 90.0,
        "description": (
            "新月から少しずつ月が満ちていく段階です。"
            "一般的には、決めた目標に向かって最初の行動を起こし、"
            "可能性を育てていく時期として捉えられます。"
        ),
    },
    {
        "id": "P03",
        "name": "上弦の月",
        "englishName": "First Quarter",
        "start": 90.0,
        "end": 135.0,
        "description": (
            "月が半分ほど満ちた段階です。"
            "一般的には、行動を続けながら課題に向き合い、"
            "必要な決断や調整を行う時期として捉えられます。"
        ),
    },
    {
        "id": "P04",
        "name": "満ちていく凸月",
        "englishName": "Waxing Gibbous",
        "start": 135.0,
        "end": 180.0,
        "description": (
            "満月へ向かって、さらに月が満ちていく段階です。"
            "一般的には、これまで積み重ねてきたものを見直し、"
            "完成に向けて磨き上げていく時期として捉えられます。"
        ),
    },
    {
        "id": "P05",
        "name": "満月",
        "englishName": "Full Moon",
        "start": 180.0,
        "end": 225.0,
        "description": (
            "月が最も満ちた状態を中心とする段階です。"
            "一般的には、物事の成果や到達点を確認し、"
            "これまでの取り組みを振り返る時期として捉えられます。"
        ),
    },
    {
        "id": "P06",
        "name": "欠けていく凸月",
        "englishName": "Waning Gibbous",
        "start": 225.0,
        "end": 270.0,
        "description": (
            "満月を過ぎ、月が少しずつ欠け始める段階です。"
            "一般的には、得られた経験や成果を整理し、"
            "周囲へ分かち合っていく時期として捉えられます。"
        ),
    },
    {
        "id": "P07",
        "name": "下弦の月",
        "englishName": "Last Quarter",
        "start": 270.0,
        "end": 315.0,
        "description": (
            "月が再び半分ほどになった段階です。"
            "一般的には、これまでの流れを振り返り、"
            "不要になったものを整理して次へ進む準備をする時期として捉えられます。"
        ),
    },
    {
        "id": "P08",
        "name": "欠けていく三日月",
        "englishName": "Waning Crescent",
        "start": 315.0,
        "end": 360.0,
        "description": (
            "新月へ戻る直前の月相です。"
            "一般的には、一つのサイクルを静かに振り返り、"
            "次の始まりに向けて休息や整理を行う時期として捉えられます。"
        ),
    },
]


PROVISIONAL_NOTE = (
    "現在表示している月相名称・説明はPoC技術検証用の仮仕様です。"
    "春華独自の正式な「月相羅針」分類・名称・説明ではありません。"
)

UNKNOWN_TIME_NOTE = (
    "出生時間不明時の候補判定方式もPoC技術検証用の暫定仕様です。"
    "春華独自の正式な出生時間不明時ルールではありません。"
)


def _phase_payload(phase: dict, angle: float | None = None) -> dict:
    payload = {
        **phase,
        "rangeText": f'{phase["start"]:.0f}°以上 {phase["end"]:.0f}°未満',
        "provisional": True,
        "classificationType": "standard_lunar_phase_poc",
        "note": PROVISIONAL_NOTE,
    }
    if angle is not None:
        payload["angle"] = float(angle) % 360.0
    return payload


def classify_phase(angle_difference: float) -> dict:
    """Classify one angle difference into the provisional 45° x 8 phases.

    判定ルール：
    ・開始角度を含む
    ・終了角度を含まない
    ・360°は0°として扱う

    This is only a PoC technical-validation classification and is not the
    formal proprietary 春華「月相羅針」specification.
    """
    angle = float(angle_difference) % 360.0
    index = min(int(angle // 45.0), 7)
    return _phase_payload(PHASES[index], angle=angle)


def _unwrap_angles(angle_differences: list[float]) -> list[float]:
    """Unwrap a sampled 0-360° angle path across the 360°/0° boundary.

    Adjacent sample movement is interpreted using the shortest signed angular
    change. With the PoC's 30-minute astronomy sampling this keeps a continuous
    path when, for example, 359° becomes 1°.
    """
    if not angle_differences:
        return []

    normalized = [float(angle) % 360.0 for angle in angle_differences]
    unwrapped = [normalized[0]]
    previous = normalized[0]

    for angle in normalized[1:]:
        delta = angle - previous
        if delta > 180.0:
            delta -= 360.0
        elif delta <= -180.0:
            delta += 360.0
        unwrapped.append(unwrapped[-1] + delta)
        previous = angle

    return unwrapped


def classify_possible_phases(angle_differences: list[float]) -> dict:
    """Return all provisional phase candidates found across sampled angles.

    The function does more than deduplicate sample classifications. It unwraps
    the continuous angle path and includes every 45° sector traversed between
    adjacent samples. This correctly handles 360° -> 0° wrap-around and avoids
    losing a crossed phase boundary merely because the exact boundary instant
    was not one of the sampled timestamps.

    This remains a PoC rule, not a formal 春華 birth-time-unknown rule.
    """
    if not angle_differences:
        raise ValueError("月相候補判定には1件以上の角度差が必要です。")

    unwrapped = _unwrap_angles(angle_differences)
    encountered_sector_numbers: list[int] = []

    def append_sector(sector_number: int) -> None:
        if sector_number not in encountered_sector_numbers:
            encountered_sector_numbers.append(sector_number)

    append_sector(int(unwrapped[0] // 45.0))

    for start, end in zip(unwrapped, unwrapped[1:]):
        start_sector = int(start // 45.0)
        end_sector = int(end // 45.0)

        if end_sector >= start_sector:
            sectors = range(start_sector, end_sector + 1)
        else:
            sectors = range(start_sector, end_sector - 1, -1)

        for sector in sectors:
            append_sector(sector)

    possible_phase_indexes: list[int] = []
    for sector_number in encountered_sector_numbers:
        phase_index = sector_number % 8
        if phase_index not in possible_phase_indexes:
            possible_phase_indexes.append(phase_index)

    possible_phases = [_phase_payload(PHASES[index]) for index in possible_phase_indexes]
    status = "stable" if len(possible_phases) == 1 else "ambiguous"

    return {
        "birth_time_known": False,
        "classification_status": status,
        "possible_phases": possible_phases,
        "sample_count": len(angle_differences),
        "angle_path_start": float(angle_differences[0]) % 360.0,
        "angle_path_end": float(angle_differences[-1]) % 360.0,
        "unknown_time_rule_provisional": True,
        "unknown_time_note": UNKNOWN_TIME_NOTE,
    }
