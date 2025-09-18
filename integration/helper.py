import time


class timeit:
    """A context manager used to measure time it takes
    to execute its with-block.
    The result is available as `time_delta` attribute.

    Args:
        label: A text label
        silent: Whether to suppress printing the result
    """

    def __init__(self, label: str | None = None, silent: bool = False):
        self.label = label
        self.silent = silent
        self.start_time: float | None = None
        self.time_delta: float | None = None

    def __enter__(self) -> "timeit":
        self.start_time = time.process_time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.time_delta = time.process_time() - self.start_time
        if not self.silent:
            print(f"{self.label or 'code block'} took {self.time_delta:.3f} seconds")
