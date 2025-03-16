import datetime
from dataclasses import dataclass
from typing import Callable, Optional

@dataclass
class _LastUpdate:
    seconds_since_start: float
    bytes_received: int
    bytes_to_receive: int

class _DownloadProgress:
    _start: datetime.datetime
    _updates: list[_LastUpdate]
    _print_func: Callable[[str], None]
    _total_bytes: int
    _last_print_time: int
    _last_print_pct: int
    _last_print_secs: int

    def __init__(self, print_func: Callable[[str], None]):
        if print_func is not None and not callable(print_func):
            raise TypeError("The print_func argument must be callable.")
        self._start = datetime.datetime.now()
        self._updates = list[_LastUpdate]()
        self._print_func = print_func
        self._total_bytes = None
        self._last_print_time = -1
        self._last_print_pct = -1
        self._last_print_secs = -1

    def __call__(self, count, block_size, total_size):
        if self._total_bytes is None:
            self._total_bytes = total_size
        bytes_received = min(count * block_size, total_size)
        bytes_to_receive = total_size - bytes_received
        if self._updates:
            prev_update = self._updates[-1]
            if bytes_received == prev_update.bytes_received:
                return
        seconds = self._seconds_since_start()
        self._updates.append(_LastUpdate(seconds, bytes_received, bytes_to_receive))
        self._check_print()

    def _check_print(self):
        if not self._updates:
            return
        prev = self._updates[-1]
        if round(prev.seconds_since_start) == self._last_print_time:
            return
        received = prev.bytes_received
        remain = prev.bytes_to_receive
        total = self._total_bytes
        percent = round((received / total) * 100)
        if percent == self._last_print_pct:
            return
        self._last_print_pct = percent
        msg = list[str]()
        total_s = str(total)
        received_s = str(received).rjust(len(total_s))
        remain_s = str(remain).rjust(len(total_s))
        msg.append(f"[{percent:3}%] (received: {received_s}, remaining: {remain_s}, total: {total_s})")
        slope = self._estimate()
        if slope is not None:
            remain_seconds = round(remain / slope)
            eta_str = str(datetime.timedelta(seconds=remain_seconds))
            msg.append(f"ETA: {eta_str}, {slope/1024.0:.1f} kB/s")
        if callable(self._print_func):
            self._print_func(" ".join(msg))
        self._last_print_time = round(prev.seconds_since_start)

    def _seconds_since_start(self) -> float:
        return (datetime.datetime.now() - self._start).total_seconds()

    def _estimate(self) -> Optional[float]:
        count = len(self._updates)
        if count < 6:
            return None
        elif count < 12:
            return self._estimate_with(self._updates)
        else:
            return self._estimate_select()
    
    def _estimate_select(self) -> Optional[float]:
        full_count = len(self._updates)
        selected = self._select_index(full_count)
        updates = [self._updates[idx] for idx in selected]
        return self._estimate_with(updates)

    def _estimate_with(self, updates: list[_LastUpdate]) -> Optional[float]:
        count = len(updates)
        if count < 4:
            return None
        slopes = list[float]()
        for idx0 in range(0, count - 1):
            u0 = updates[idx0]
            for idx1 in range(idx0 + 1, count):
                u1 = updates[idx1]
                delta_bytes = u1.bytes_received - u0.bytes_received
                delta_seconds = u1.seconds_since_start - u0.seconds_since_start
                slope = delta_bytes / delta_seconds
                slopes.append(slope)
        slopes.sort()
        idx_median = (len(slopes) - 1) // 2
        return slopes[idx_median]
    
    def _select_index(self, count: int) -> list[int]:
        next_idx = 0
        select_set = set[int]()
        while next_idx < count:
            idx = next_idx
            next_idx = max(idx + 1, ((idx * 3) // 2))
            select_set.add(idx)
            select_set.add(count - 1 - idx)
        return sorted(select_set)
