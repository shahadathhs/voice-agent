import argparse
import json
import re
from pathlib import Path


def normalize(text: str) -> list[str]:
    return re.sub(r"[^\w\s]", "", text.lower()).split()


def wer(reference: str, hypothesis: str) -> float:
    ref = normalize(reference)
    hyp = normalize(hypothesis)
    if not ref:
        return 0.0 if not hyp else 1.0

    matrix = [[0.0] * (len(hyp) + 1) for _ in range(len(ref) + 1)]
    for i in range(len(ref) + 1):
        matrix[i][0] = i
    for j in range(len(hyp) + 1):
        matrix[0][j] = j
    for i in range(1, len(ref) + 1):
        for j in range(1, len(hyp) + 1):
            cost = 0 if ref[i - 1] == hyp[j - 1] else 1
            matrix[i][j] = min(
                matrix[i - 1][j] + 1,
                matrix[i][j - 1] + 1,
                matrix[i - 1][j - 1] + cost,
            )
    return matrix[len(ref)][len(hyp)] / len(ref)


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Word Error Rate: pass --text "ref|||hyp" or --pairs file.json'
    )
    parser.add_argument("--text", help='Format: "reference|||hypothesis"')
    parser.add_argument("--pairs", help='JSON file: [{"reference": ..., "hypothesis": ...}, ...]')
    args = parser.parse_args()

    if args.text:
        reference, hypothesis = args.text.split("|||")
        print(f"WER: {wer(reference, hypothesis):.3f}")
        return

    if args.pairs:
        pairs = json.loads(Path(args.pairs).read_text())
        scores = [wer(p["reference"], p["hypothesis"]) for p in pairs]
        for pair, score in zip(pairs, scores, strict=True):
            print(f"{score:.3f}  {pair['reference'][:60]!r}")
        print(f"\nMean WER: {sum(scores) / len(scores):.3f}")
        return

    parser.error("provide --text or --pairs")


if __name__ == "__main__":
    main()
