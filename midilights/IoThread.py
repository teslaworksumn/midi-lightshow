import threading
import time


class IoThread:
    def __init__(self, backend, name, output_func, mapper=None):
        self._mido_backend = backend
        self._name = name
        self._output_func = output_func
        self._mapper = mapper
        self._channel_values = []
        self._stop = threading.Event()

        self._thread = threading.Thread(target=self._run)
        self._thread.daemon = True
        self._thread.setName("midils input thread for {0}".format(self._name))

    def start(self):
        self._stop.clear()
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _handle_message(self, message):
        """Updates channel values when a MIDI message is received"""
        if message.type in ['note_on', 'note_off']:
            channels = self._get_channels(message.note)
            if channels is None:
                print("Note not mapped:", message.note)
            else:
                for channel in channels:
                    self._modify_channel_value(channel, message.type == 'note_on')

    def _modify_channel_value(self, channel, is_on):
        """Updates the value of a channel, extending the underlying array of values as necessary"""
        num_ch = len(self._channel_values)
        if channel >= num_ch:
            diff = channel - num_ch + 1
            extension = [1] * diff
            self._channel_values.extend(extension)
        value = self._channel_values[channel]
        if is_on:
            value *= 16
        else:
            value /= 16
        value = int(value)
        self._channel_values[channel] = value

    def _get_channels(self, note):
        """Maps the note to a set of output channels if a mapper exists.
        Returns None if mapping doesn't exist"""
        if self._mapper is None:
            return note
        return self._mapper.map(note)

    def _run(self):
        """Write the channel values to the output at set intervals until stopped"""
        self._mido_backend.open_input(self._name, callback=self._handle_message)
        while not self._stop.is_set():
            if len(self._channel_values) > 0:
                max_bound = [254 if x > 254 else x for x in self._channel_values]
                min_bound = [0 if x == 1 else x for x in max_bound]
                self._output_func(min_bound)
            time.sleep(0.1)


def _velocity_to_output(velocity):
    """Approximately maps keyboard velocity in range [1, 120]
    to output value in range [0, 255]"""
    return (velocity - 1) * 2 + 1
