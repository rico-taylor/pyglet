# ----------------------------------------------------------------------------
# pyglet
# Copyright (c) 2006-2008 Alex Holkner
# Copyright (c) 2008-2020 pyglet contributors
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in
#    the documentation and/or other materials provided with the
#    distribution.
#  * Neither the name of pyglet nor the names of its
#    contributors may be used to endorse or promote products
#    derived from this software without specific prior written
#    permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
# ----------------------------------------------------------------------------

"""Multi-format decoder using Gstreamer.
"""
import queue
from threading import Event, Thread

from ..exceptions import MediaDecodeException
from .base import StreamingSource, AudioData, AudioFormat, StaticSource
from . import MediaEncoder, MediaDecoder

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib


class GStreamerDecodeException(MediaDecodeException):
    pass


class GLibMainLoopThread(Thread):
    """A background Thread for a GLib MainLoop"""
    def __init__(self):
        super().__init__(daemon=True)
        self.mainloop = GLib.MainLoop.new(None, False)
        self.start()

    def run(self):
        self.mainloop.run()


class GStreamerSource(StreamingSource):

    _sentinal = object()

    def __init__(self, filename, file=None):
        self._pipeline = Gst.Pipeline()

        # Create the major parts of the pipeline:
        self.filesrc = Gst.ElementFactory.make("filesrc", None)
        self.decoder = Gst.ElementFactory.make("decodebin", None)
        self.audio_converter = Gst.ElementFactory.make("audioconvert", None)
        self.sink = Gst.ElementFactory.make("appsink", None)
        if not all((self.filesrc, self.decoder, self.audio_converter, self.sink)):
            raise GStreamerDecodeException("Could not initialize GStreamer.")

        # Set callbacks for EOS and errors:
        self._pipeline.bus.add_signal_watch()
        self._pipeline.bus.connect("message::eos", self._message)
        self._pipeline.bus.connect("message::error", self._message)

        # Set the file path to load:
        self.filesrc.set_property("location", filename)

        # Set decoder callback handlers:
        self.decoder.connect("pad-added", self._pad_added)
        self.decoder.connect("no-more-pads", self._no_more_pads)
        self.decoder.connect("unknown-type", self._unknown_type)

        # Set the sink's capabilities and behavior:
        self.sink.set_property('caps', Gst.Caps.from_string('audio/x-raw'))
        self.sink.set_property('drop', False)
        self.sink.set_property('sync', False)
        self.sink.set_property('max-buffers', 5)
        self.sink.set_property('emit-signals', True)
        # The callback to receive decoded data:
        self.sink.connect("new-sample", self._new_sample)

        # Add all components to the pipeline:
        self._pipeline.add(self.filesrc)
        self._pipeline.add(self.decoder)
        self._pipeline.add(self.audio_converter)
        self._pipeline.add(self.sink)
        # Link together necessary components:
        self.filesrc.link(self.decoder)
        self.audio_converter.link(self.sink)

        # Callback to notify once the sink is ready:
        self.caps_handler = self.sink.get_static_pad("sink").connect("notify::caps", self._notify_caps)

        # Set by callbacks:
        self._pads = False
        self._caps = False
        self._pipeline.set_state(Gst.State.PLAYING)
        self._queue = queue.Queue(5)
        self._finished = Event()
        # Wait until the is_ready event is set by a callback:
        self._is_ready = Event()
        if not self._is_ready.wait(timeout=1):
            raise GStreamerDecodeException('Initialization Error')

    def __del__(self):
        try:
            self._pipeline.bus.remove_signal_watch()
            self.filesrc.set_property("location", None)
            self.sink.get_static_pad("sink").disconnect(self.caps_handler)

            while not self._queue.empty():
                self._queue.get_nowait()

            self._pipeline.set_state(Gst.State.NULL)

        except AttributeError:
            pass

    def _notify_caps(self, pad, *args):
        """notify::caps callback"""
        self._caps = True
        info = pad.get_current_caps().get_structure(0)

        self._duration = pad.get_peer().query_duration(Gst.Format.TIME).duration / Gst.SECOND
        channels = info.get_int('channels')[1]
        sample_rate = info.get_int('rate')[1]
        sample_size = int("".join(filter(str.isdigit, info.get_string('format'))))

        self.audio_format = AudioFormat(channels=channels,
                                        sample_size=sample_size,
                                        sample_rate=sample_rate)

        # Allow __init__ to complete:
        self._is_ready.set()

    def _pad_added(self, element, pad):
        """pad-added callback"""
        name = pad.query_caps(None).to_string()
        if name.startswith('audio/x-raw'):
            nextpad = self.audio_converter.get_static_pad('sink')
            if not nextpad.is_linked():
                self._pads = True
                pad.link(nextpad)

    def _no_more_pads(self, element):
        """Finished Adding pads"""
        if not self._pads:
            raise GStreamerDecodeException('No Streams Found')

    def _new_sample(self, sink):
        """new-sample callback"""
        # Query the sample, and get it's buffer:
        buffer = sink.emit('pull-sample').get_buffer()
        # Extract a copy of the memory in the buffer:
        mem = buffer.extract_dup(0, buffer.get_size())
        self._queue.put(mem)
        return Gst.FlowReturn.OK

    @staticmethod
    def _unknown_type(uridecodebin, decodebin, caps):
        """unknown-type callback for unreadable files"""
        streaminfo = caps.to_string()
        if not streaminfo.startswith('audio/'):
            return
        raise GStreamerDecodeException(streaminfo)

    def _message(self, bus, message):
        """The main message callback"""
        if message.type == Gst.MessageType.EOS:

            self._queue.put(self._sentinal)
            if not self._caps:
                raise GStreamerDecodeException("Appears to be an unsupported file")

        elif message.type == Gst.MessageType.ERROR:
            raise GStreamerDecodeException(message.parse_error())

    def get_audio_data(self, num_bytes, compensation_time=0.0):
        if self._finished.is_set():
            return None

        data = bytes()
        while len(data) < num_bytes:
            packet = self._queue.get()
            if packet == self._sentinal:
                self._finished.set()
                break
            data += packet

        if not data:
            return None

        timestamp = self._pipeline.query_position(Gst.Format.TIME).cur / Gst.SECOND
        duration = self.audio_format.bytes_per_second / len(data)

        return AudioData(data, len(data), timestamp, duration, [])

    def seek(self, timestamp):
        # First clear any data in the queue:
        while not self._queue.empty():
            self._queue.get_nowait()

        self._pipeline.seek_simple(Gst.Format.TIME,
                                   Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                                   timestamp * Gst.SECOND)
        self._finished.clear()


#########################################
#   Decoder class:
#########################################

class GStreamerDecoder(MediaDecoder):

    def __init__(self):
        Gst.init(None)
        self._glib_loop = GLibMainLoopThread()

    def get_file_extensions(self):
        return '.mp3', '.flac', '.ogg', '.m4a'

    def decode(self, file, filename, streaming=True):

        if not any(filename.endswith(ext) for ext in self.get_file_extensions()):
            # Do not try to decode other formats or Video for now.
            raise GStreamerDecodeException('Unsupported format.')

        if streaming:
            return GStreamerSource(filename, file)
        else:
            return StaticSource(GStreamerSource(filename, file))

    def __del__(self):
        self._glib_loop.mainloop.quit()


def get_decoders():
    return [GStreamerDecoder()]


def get_encoders():
    return []
