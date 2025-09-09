import os
import subprocess
from logging import getLogger
from . import SynthesizerBase

logger = getLogger(__name__)


class Synthesizer(SynthesizerBase):
    """
    Synthesizer that uses an external command-line tool.

    Expects the command specified by 'bin' and 'args' to:
    1. Read the text to be synthesized from standard input (stdin).
    2. Generate the audio file and save it to the path specified by 'output_path',
       or use the 'output_path' provided in the 'args' list.
       (This implementation passes the output_path as the last argument if {output_path} is not found in args).

    Parameters:
        bin (str): The path to the executable (e.g., '/usr/bin/espeak-ng', 'C:\\Program Files\\...\\my_tts.exe').
        args (list): A list of string arguments to pass to the executable.
                     Use '{output_path}' as a placeholder within the list if the command
                     requires the output path as a specific argument in the middle.
                     If '{output_path}' is not present, the path will be appended as the last argument.
                     Example: ["-v", "en", "-w", "{output_path}"]
                     Example: ["--output", "{output_path}", "--format", "wav"]
                     If output path is handled differently by the command, ensure args reflect that.
        shell (bool, optional): If True, the command will be executed through the shell.
                                Defaults to False. Use with caution.
        encoding (str, optional): The text encoding to use for the input sent to stdin.
                                  Defaults to 'utf-8'.
    """

    def __init__(
        self, bin="", args=None, shell=False, cwd="", encoding="utf-8", **kwargs
    ):
        self.bin = bin
        self.args = args if args is not None else []
        self.shell = shell
        self.encoding = encoding
        self.cwd = (cwd and os.path.expanduser(cwd)) or None
        # Store any other potential kwargs if needed for dynamic argument substitution (advanced)
        self.extra_params = kwargs

    def _prepare_command(self, output_path: str) -> list:
        """Prepares the full command list."""
        if not self.bin:
            raise ValueError(
                "The 'bin' parameter (executable path) must be provided for the 'cmd' synthesizer."
            )

        # Format args, replacing {output_path} if present
        formatted_args = []
        output_path_placeholder_used = False
        for arg in self.args:
            if isinstance(arg, str) and "{output_path}" in arg:
                formatted_args.append(arg.format(output_path=output_path))
                output_path_placeholder_used = True
            else:
                formatted_args.append(arg)

        # If {output_path} wasn't a placeholder in args, append the output_path
        if not output_path_placeholder_used:
            formatted_args.append(output_path)

        # Construct the full command
        cmd = [self.bin] + formatted_args
        return cmd

    def synthesize(self, text: str, output_path: str):
        """
        Synthesizes text using the configured command-line tool.

        Args:
            text: The text to synthesize.
            output_path: The path where the audio file should be saved.
        """
        cmd = self._prepare_command(output_path)

        logger.info(
            f"Executing TTS command: {' '.join(cmd) if not self.shell else cmd}"
        )
        logger.debug(f"Input text: {text}")

        try:
            # Ensure the output directory exists
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)

            # Use Popen for more control over stdin
            with subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,  # Handle text mode for stdin/stdout/stderr
                encoding=self.encoding,
                shell=self.shell,  # Be cautious with shell=True
                cwd=self.cwd,
            ) as process:
                # Send text to the command's stdin
                stdout, stderr = process.communicate(input=text)

                # Check the return code
                if process.returncode != 0:
                    error_msg = (
                        f"Command '{' '.join(cmd)}' failed with return code {process.returncode}.\n"
                        f"Stdout: {stdout}\nStderr: {stderr}"
                    )
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)
                else:
                    logger.info(f"Command '{' '.join(cmd)}' completed successfully.")
                    if stdout.strip():
                        logger.debug(f"Command stdout: {stdout}")
                    if stderr.strip():
                        logger.debug(
                            f"Command stderr: {stderr}"
                        )  # Might be warnings, not errors

        except FileNotFoundError:
            error_msg = f"The executable '{self.bin}' was not found. Please check the 'bin' path."
            logger.error(error_msg)
            raise RuntimeError(
                error_msg
            ) from None  # Suppress the original FileNotFoundError chain
        except Exception as e:
            logger.error(
                f"An error occurred while running the command: {e}", exc_info=True
            )
            raise RuntimeError(f"Command execution failed: {e}") from e

    def is_available(self) -> bool:
        """
        Checks if the configured executable exists and is accessible.
        Note: This doesn't verify the executable *works* correctly, just its presence.
        """
        if not self.bin:
            logger.warning("is_available: 'bin' path is not set.")
            return False
        # Use shutil.which for a more robust check if the path is just a command name
        # or os.access for checking execute permissions on a full path.
        if os.path.isabs(self.bin):
            # If it's an absolute path, check if the file exists and is executable
            is_executable = os.path.isfile(self.bin) and os.access(self.bin, os.X_OK)
            logger.debug(f"is_available (absolute path): {self.bin} -> {is_executable}")
            return is_executable
        else:
            # If it's not absolute, treat it like a command name and search PATH
            found_path = self.shutil.which(self.bin)
            is_found = found_path is not None
            logger.debug(
                f"is_available (command): {self.bin} -> {is_found} ({found_path})"
            )
            return is_found

    def _get_shutil(self):
        """Lazy import for shutil."""
        import shutil

        return shutil
