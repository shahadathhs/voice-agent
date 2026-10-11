import re

_SENTENCE_END = re.compile(r'[.!?…]+["\')\]]*(?=\s)|\n+')


class SentenceChunker:
    def __init__(self, min_chars: int = 12) -> None:
        self.min_chars = min_chars
        self._buf = ""

    def add(self, delta: str) -> list[str]:
        self._buf += delta
        return self._drain(final=False)

    def flush(self) -> list[str]:
        return self._drain(final=True)

    def _drain(self, final: bool) -> list[str]:
        pieces: list[str] = []
        while True:
            match = _SENTENCE_END.search(self._buf)
            if match is None:
                break
            piece = self._buf[: match.end()]
            while len(piece.strip()) < self.min_chars:
                extended = _SENTENCE_END.search(self._buf, match.end())
                if extended is None:
                    piece = None
                    break
                match = extended
                piece = self._buf[: match.end()]
            if piece is None:
                if final:
                    pieces.append(self._buf)
                    self._buf = ""
                return pieces
            pieces.append(piece)
            self._buf = self._buf[match.end() :]
        if final and self._buf.strip():
            pieces.append(self._buf)
            self._buf = ""
        return pieces
