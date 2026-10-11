from app.pipeline.chunker import SentenceChunker


def test_single_sentence_chunking() -> None:
    chunker = SentenceChunker()
    assert chunker.add("Hello there. ") == ["Hello there."]
    assert chunker.flush() == []


def test_across_deltas() -> None:
    chunker = SentenceChunker()
    assert chunker.add("Hello the") == []
    assert chunker.add("re. How are") == ["Hello there."]
    assert chunker.add(" you?") == []
    assert chunker.flush() == [" How are you?"]


def test_flush_returns_remainder() -> None:
    chunker = SentenceChunker()
    chunker.add("This has no ending")
    assert chunker.flush() == ["This has no ending"]
    assert chunker.add("x") == []
    assert chunker.flush() == ["x"]


def test_short_fragments_merge() -> None:
    chunker = SentenceChunker()
    out = chunker.add("Hi. Ok. This is a proper sentence that ends here. ")
    assert out == ["Hi. Ok. This is a proper sentence that ends here."]
    assert chunker.flush() == []


def test_multiple_sentences_single_delta() -> None:
    chunker = SentenceChunker()
    out = chunker.add("First one here. Second one follows! Third is last?")
    assert out == ["First one here.", " Second one follows!"]
    assert chunker.flush() == [" Third is last?"]


def test_newline_is_boundary() -> None:
    chunker = SentenceChunker()
    out = chunker.add("List item number one\nand more text")
    assert out == ["List item number one\n"]
    assert chunker.flush() == ["and more text"]


def test_abbreviations_merge_into_following_sentence() -> None:
    chunker = SentenceChunker(min_chars=12)
    out = chunker.add("e.g. something longer follows here. ")
    assert out == ["e.g. something longer follows here."]
    assert chunker.flush() == []


def test_flush_after_partial_short_piece() -> None:
    chunker = SentenceChunker()
    chunker.add("Ok.")
    assert chunker.flush() == ["Ok."]
