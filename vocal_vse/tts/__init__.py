import abc


class BaseTTSHandler(abc.ABC):
    """Abstract base class for TTS handlers."""

    @abc.abstractmethod
    def synthesize(self, text: str, output_path: str, **kwargs) -> None:
        """
        Synthesize text to speech and save to output_path.

        Args:
            text: The text to synthesize.
            output_path: The full path to save the audio file (e.g., .wav).
        """
        pass

    # Optional: Add methods for checking requirements, etc.
    @abc.abstractmethod
    def is_available(self) -> bool:
        """Check if the handler's dependencies are installed."""
        pass

    def __getattr__(self, name):
        f = not name.startswith("_get_") and getattr(self, f"_get_{name}", None)
        if f:
            setattr(self, name, None)
            v = f()
            setattr(self, name, v)
            return v
        try:
            m = super().__getattr__  # type: ignore
        except AttributeError:
            pass
        else:
            return m(name)
        c = self.__class__
        raise AttributeError(
            f"{c.__module__}.{c.__qualname__} has no attribute '{name}'"
        )
